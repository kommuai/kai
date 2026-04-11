import unittest

from support_runtime.agent_loop import AgentLoopDependencies, ReActAgentLoop
from support_runtime.agent_tools import AgentToolRegistry
from support_runtime.retrieval import HybridRetriever, SimpleReranker


class _DummyProvider:
    def __init__(self):
        self.calls = 0

    def chat(self, _system: str, _user: str, **_kwargs):
        return self.chat_messages([], **_kwargs)

    def chat_messages(self, messages, **_kwargs):
        self.calls += 1
        if self.calls == 1:
            return '{"action":"tool","tool":"search_faq","args":{"query":"install"}}'
        return '{"action":"final","decision":"clarifying_question","question":"What car model and year do you drive?","confidence":0.7}'


class RouteAgentDebugTests(unittest.TestCase):
    def test_route_agent_returns_trace_steps(self):
        loop = ReActAgentLoop(
            AgentLoopDependencies(
                provider=_DummyProvider(),
                tools=AgentToolRegistry(HybridRetriever(provider=None), SimpleReranker(provider=None)),
                system_prompt="test",
            )
        )
        out = loop.run(text="can i install now?", lang="EN", user_id="u1")["result"]
        route_meta = out.metadata.get("agentic_route", {})
        self.assertIn("steps", route_meta)
        self.assertIsInstance(route_meta["steps"], list)


if __name__ == "__main__":
    unittest.main()
