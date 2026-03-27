from __future__ import annotations

from dataclasses import asdict

from google_sheets import fetch_warranty_all
from session_state import add_message_to_history, get_history, update_session_summary
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

    def execute(self, text: str, lang: str = "EN", user_id: str = "") -> RuntimeResult:
        if not self.graph:
            self.startup()
        # Refresh clock in system prompt every turn so "today/tomorrow" matches wall time.
        self.graph.deps.system_prompt = build_system_prompt(self.agent_tools.list_schemas())

        history = get_history(user_id) if user_id else []

        if user_id:
            add_message_to_history(user_id, "user", text)
            update_session_summary(user_id, "user", text)

        state = self.graph.run(
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
