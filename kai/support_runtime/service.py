from __future__ import annotations

from dataclasses import asdict

from kai.lib.google_sheets import fetch_warranty_all
from kai.lib.session_state import (
    add_message_to_history,
    build_short_term_context,
    get_history,
    update_session_summary,
)
from kai.support_runtime.canonical_faq import (
    enrich_query_with_history,
    format_canonical_hint,
    pick_best_canonical,
    pick_faq_first_runtime,
)
from kai.support_runtime.compiler import compile_canonical_knowledge
from kai.support_runtime.agent_loop import AgentLoopDependencies, ReActAgentLoop
from kai.support_runtime.agent_prompts import build_system_prompt
from kai.support_runtime.agent_tools import AgentToolRegistry
from kai.support_runtime.models import RuntimeResult
from kai.support_runtime.providers import build_provider
from kai.support_runtime.retrieval import HybridRetriever, SimpleReranker


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

                faq = self.agent_tools.search_faq(query=text)
                hit = pick_faq_first_runtime(faq, wants_video=wants_video, wants_link=wants_link)
                if hit:
                    ans = hit["canonical_answer"]
                    return self._return_canonical_answer(
                        user_id, text, ans, hit, wants_video=wants_video
                    )

                if wants_video:
                    faq2 = self.agent_tools.search_faq(query="self install video guide")
                    hit2 = pick_faq_first_runtime(
                        faq2, wants_video=True, wants_link=True
                    )
                    if hit2:
                        return self._return_canonical_answer(
                            user_id, text, hit2["canonical_answer"], hit2, wants_video=True
                        )
            except Exception:
                pass

        if user_id:
            add_message_to_history(user_id, "user", text)
            update_session_summary(user_id, "user", text)
            history = get_history(user_id)

        session_context = build_short_term_context(user_id) if user_id else ""
        try:
            faq_query = enrich_query_with_history(text, history)
            faq_for_react = self.agent_tools.search_faq(query=faq_query)
            canon = pick_best_canonical(faq_for_react)
            if canon:
                hint = format_canonical_hint(canon)
                session_context = f"{session_context}\n\n{hint}".strip() if session_context else hint
        except Exception:
            pass

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

    def _return_canonical_answer(
        self,
        user_id: str,
        text: str,
        answer: str,
        hit: dict,
        *,
        wants_video: bool = False,
    ) -> RuntimeResult:
        if user_id:
            add_message_to_history(user_id, "user", text)
            update_session_summary(user_id, "user", text)
            add_message_to_history(user_id, "assistant", answer)
            update_session_summary(user_id, "assistant", answer)
        score = float(hit.get("score") or 0.0)
        sid = str(hit.get("source_id") or "faq")
        return RuntimeResult(
            decision="direct_answer",
            answer=answer,
            confidence=0.9,
            source_ids=[sid],
            tool_needed=False,
            escalate_needed=False,
            capability_used="canonical_answer",
            fallback_reason="",
            metadata={
                "faq_first": True,
                "faq_top_score": score,
                "faq_source_id": sid,
                "faq_intent_id": hit.get("intent_id"),
                "faq_wants_video": wants_video,
            },
        )

    @staticmethod
    def result_dict(result: RuntimeResult) -> dict:
        return asdict(result)
