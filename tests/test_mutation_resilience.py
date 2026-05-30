import unittest

from kai.support_runtime.agent_loop import AgentLoopDependencies, ReActAgentLoop
from kai.support_runtime.agent_tools import AgentToolRegistry
from kai.support_runtime.retrieval import HybridRetriever, SimpleReranker


class _FailingProvider:
    def __init__(self):
        self.calls = 0

    def chat(self, system_prompt, user_prompt, temperature=0.2, max_tokens=500):
        return self.chat_messages([], temperature=temperature, max_tokens=max_tokens)

    def chat_messages(self, messages, temperature=0.2, max_tokens=1200):
        self.calls += 1
        if self.calls == 1:
            return '{"action":"tool","tool":"search_faq","args":{"query":"vehicle specs"}}'
        return '{"action":"final","decision":"clarifying_question","question":"What is your exact vehicle model and year?","confidence":0.66}'


class MutationResilienceTests(unittest.TestCase):
    def test_tool_failure_degrades_gracefully(self):
        provider = _FailingProvider()
        reg = AgentToolRegistry(HybridRetriever(provider=None), SimpleReranker(provider=None))
        out = ReActAgentLoop(AgentLoopDependencies(provider=provider, tools=reg, system_prompt="test")).run(
            text="is my car supported?", lang="EN", user_id="r1"
        )["result"]
        self.assertIn(out.decision, {"clarifying_question", "direct_answer", "escalate_human"})
        self.assertIsInstance(out.answer, str)
        self.assertTrue(len(out.answer) > 0)


if __name__ == "__main__":
    unittest.main()

