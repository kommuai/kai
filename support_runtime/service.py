from __future__ import annotations

from dataclasses import asdict
import re

from google_sheets import fetch_warranty_all
from session_state import (
    add_message_to_history,
    build_short_term_context,
    get_history,
    update_session_summary,
)
from support_runtime.compiler import compile_canonical_knowledge
from support_runtime.agent_loop import AgentLoopDependencies, ReActAgentLoop
from support_runtime.agent_prompts import build_system_prompt
from support_runtime.agent_tools import AgentToolRegistry
from support_runtime.models import RuntimeResult
from support_runtime.providers import build_provider
from support_runtime.retrieval import HybridRetriever, SimpleReranker


class SupportRuntimeService:
    def __init__(self) -> None:
        self.provider = build_provider()
        self.retriever = HybridRetriever(provider=self.provider)
        self.reranker = SimpleReranker(provider=self.provider)
        self.agent_tools = AgentToolRegistry(retriever=self.retriever, reranker=self.reranker)
        self.graph = None

    def startup(self) -> dict:
        counts = compile_canonical_knowledge()
        try:
            fetch_warranty_all()
        except Exception:
            pass
        self.retriever.load()
        deps = AgentLoopDependencies(
            provider=self.provider,
            tools=self.agent_tools,
            system_prompt=build_system_prompt(self.agent_tools.list_schemas()),
        )
        self.graph = ReActAgentLoop(deps)
        return counts

    def refresh_knowledge(self) -> dict:
        return self.startup()

    @staticmethod
    def _extract_answer_from_faq_chunk_text(text: str) -> str:
        t = (text or "").strip()
        if not t:
            return ""
        m = re.search(r"(?:^|\n)A:\s*(.*)\s*$", t, flags=re.S)
        if m:
            return (m.group(1) or "").strip()
        return t

    def execute(self, text: str, lang: str = "EN", user_id: str = "") -> RuntimeResult:
        if not self.graph:
            self.startup()
        # Refresh clock in system prompt every turn so "today/tomorrow" matches wall time.
        self.graph.deps.system_prompt = build_system_prompt(self.agent_tools.list_schemas())

        history = get_history(user_id) if user_id else []
        # From the second message in a session onward, always use the ReAct loop so
        # prior turns + session summary/facts stay in context (no FAQ-first shortcut).
        is_follow_up = bool(history)

        # FAQ-first deterministic answer when confident (first message only).
        if not is_follow_up:
            try:
                ql = (text or "").lower()
                wants_video = any(k in ql for k in ("video", "youtube", "youtu"))
                wants_link = wants_video or any(k in ql for k in ("guide", "link"))

                query = text
                faq = self.agent_tools.search_faq(query=query)
                results = (faq or {}).get("results") or []

                def _try_pick(res: list[dict]) -> RuntimeResult | None:
                    if not wants_link:
                        return None
                    for r in res[:4]:
                        if not isinstance(r, dict):
                            continue
                        meta = (r.get("metadata") or {}) if isinstance(r.get("metadata"), dict) else {}
                        if meta.get("category") != "known_faq_intent":
                            continue
                        score = float(r.get("score") or 0.0)
                        ans = self._extract_answer_from_faq_chunk_text(str(r.get("text") or ""))
                        has_url = "http://" in ans.lower() or "https://" in ans.lower()
                        if wants_video and ("youtu" not in ans.lower()) and ("video" not in ans.lower()):
                            continue
                        if has_url and score >= 0.45 and ans:
                            return RuntimeResult(
                                decision="direct_answer",
                                answer=ans,
                                confidence=0.9,
                                source_ids=[str(r.get("source_id") or "faq")],
                                tool_needed=False,
                                escalate_needed=False,
                                capability_used="canonical_answer",
                                fallback_reason="",
                                metadata={
                                    "faq_first": True,
                                    "faq_top_score": score,
                                    "faq_source_id": str(r.get("source_id") or ""),
                                    "faq_wants_link": True,
                                    "faq_wants_video": wants_video,
                                },
                            )
                    return None

                if (faq or {}).get("ok") and results:
                    picked = _try_pick(results)
                    if picked:
                        if user_id:
                            add_message_to_history(user_id, "user", text)
                            update_session_summary(user_id, "user", text)
                            add_message_to_history(user_id, "assistant", picked.answer)
                            update_session_summary(user_id, "assistant", picked.answer)
                        return picked

                if wants_video:
                    faq2 = self.agent_tools.search_faq(query="self install video guide")
                    results2 = (faq2 or {}).get("results") or []
                    if (faq2 or {}).get("ok") and results2:
                        picked2 = _try_pick(results2)
                        if picked2:
                            if user_id:
                                add_message_to_history(user_id, "user", text)
                                update_session_summary(user_id, "user", text)
                                add_message_to_history(user_id, "assistant", picked2.answer)
                                update_session_summary(user_id, "assistant", picked2.answer)
                            return picked2
            except Exception:
                pass

        if user_id:
            add_message_to_history(user_id, "user", text)
            update_session_summary(user_id, "user", text)
            history = get_history(user_id)

        session_context = build_short_term_context(user_id) if user_id else ""

        state = self.graph.run(
            text=text,
            lang=lang,
            user_id=user_id,
            conversation_history=history,
            session_context=session_context,
        )
        result = state.get("result")
        if isinstance(result, RuntimeResult):
            if user_id and result.answer:
                add_message_to_history(user_id, "assistant", result.answer)
                update_session_summary(user_id, "assistant", result.answer)
            return result
        if isinstance(result, dict):
            return RuntimeResult(**result)
        return RuntimeResult(
            decision="escalate_human",
            answer="I could not process this request safely. Escalating to human support.",
            confidence=0.1,
            escalate_needed=True,
            capability_used="runtime_service",
            fallback_reason="invalid_result",
        )

    @staticmethod
    def result_dict(result: RuntimeResult) -> dict:
        return asdict(result)
