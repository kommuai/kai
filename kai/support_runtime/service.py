from __future__ import annotations

from dataclasses import asdict
from typing import TYPE_CHECKING

from kai.support_runtime.agent_context import assert_prompt_sources_only, build_agent_system_prompt
from kai.lib.session_state import (
    add_message_to_history,
    ensure_active_session,
    get_history,
    update_session_summary,
)
from kai.services.turn_ingest import ingest_user_turn
from kai.support_runtime.compiler import compile_canonical_knowledge
from kai.support_runtime.agent_loop import AgentLoopDependencies, ReActAgentLoop
from kai.support_runtime.agent_tools import AgentToolRegistry
from kai.content.faq import invalidate_faq_cache
from kai.support_runtime.models import RuntimeResult
from kai.support_runtime.providers import build_provider
from kai.support_runtime.retrieval import HybridRetriever, SimpleReranker

if TYPE_CHECKING:
    from kai.support_runtime.providers import ChatProvider


class SupportRuntimeService:
    def __init__(self) -> None:
        self._provider: ChatProvider | None = None
        self._retriever: HybridRetriever | None = None
        self._reranker: SimpleReranker | None = None
        self.agent_tools: AgentToolRegistry | None = None
        self.agent_loop: ReActAgentLoop | None = None
        self.graph: ReActAgentLoop | None = None  # back-compat alias

    def _ensure_stack(self) -> None:
        if self._provider is not None:
            return
        self._provider = build_provider()
        self._retriever = HybridRetriever(provider=self._provider)
        self._reranker = SimpleReranker(provider=self._provider)

    @property
    def provider(self) -> ChatProvider:
        self._ensure_stack()
        assert self._provider is not None
        return self._provider

    @property
    def retriever(self) -> HybridRetriever:
        self._ensure_stack()
        assert self._retriever is not None
        return self._retriever

    @property
    def reranker(self) -> SimpleReranker:
        self._ensure_stack()
        assert self._reranker is not None
        return self._reranker

    def _rebuild_agent_loop(self) -> None:
        self._ensure_stack()
        self.agent_tools = AgentToolRegistry(retriever=self.retriever, reranker=self.reranker)
        deps = AgentLoopDependencies(
            provider=self.provider,
            tools=self.agent_tools,
            system_prompt=build_agent_system_prompt(self.agent_tools.list_schemas()),
        )
        self.agent_loop = ReActAgentLoop(deps)
        self.graph = self.agent_loop

    def startup(self, *, compile_kb: bool = True, warm_warranty: bool = False) -> dict:
        counts = {"intents": 0, "chunks": 0}
        if compile_kb:
            counts = compile_canonical_knowledge()
            invalidate_faq_cache()
        if warm_warranty:
            try:
                from kai.lib.google_sheets import fetch_warranty_all

                fetch_warranty_all()
            except Exception:
                pass
        self._ensure_stack()
        self.retriever.load()
        assert_prompt_sources_only()
        self._rebuild_agent_loop()
        return counts

    def refresh_knowledge(self) -> dict:
        from kai.workspace.tools_config import needs_warranty_cache

        return self.startup(compile_kb=True, warm_warranty=needs_warranty_cache())

    def execute(self, text: str, lang: str = "EN", user_id: str = "") -> RuntimeResult:
        if not self.agent_loop:
            self.startup()
        assert self.agent_loop is not None and self.agent_tools is not None
        self.agent_loop.deps.system_prompt = build_agent_system_prompt(self.agent_tools.list_schemas())

        if user_id:
            ensure_active_session(user_id)
            ingest_user_turn(user_id, text, record_history=True)
            history = get_history(user_id)
        else:
            history = []

        self.agent_tools.set_context(user_id=user_id)

        state = self.agent_loop.run(
            text=text,
            lang=lang,
            user_id=user_id,
            conversation_history=history,
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
