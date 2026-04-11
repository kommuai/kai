import unittest

from support_runtime.agent_loop import AgentLoopDependencies, ReActAgentLoop
from support_runtime.agent_tools import AgentToolRegistry
from support_runtime.retrieval import HybridRetriever, SimpleReranker


class _FakeProvider:
    def __init__(self, responses):
        self.responses = list(responses)

    def chat(self, system_prompt, user_prompt, temperature=0.2, max_tokens=500):
        return self.chat_messages(
            [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            temperature=temperature, max_tokens=max_tokens,
        )

    def chat_messages(self, messages, temperature=0.2, max_tokens=1200):
        if self.responses:
            return self.responses.pop(0)
        return '{"action":"final","decision":"clarifying_question","question":"What do you need?","confidence":0.5}'


class AgentLoopTests(unittest.TestCase):
    def test_react_loop_tool_then_answer(self):
        provider = _FakeProvider(
            [
                '{"action":"tool","tool":"search_faq","args":{"query":"install booking"}}',
                '{"action":"final","decision":"direct_answer","answer":"Install by appointment.","confidence":0.92,"source_ids":["intent:install_booking"]}',
            ]
        )
        registry = AgentToolRegistry(HybridRetriever(provider=None), SimpleReranker(provider=None))
        loop = ReActAgentLoop(
            AgentLoopDependencies(provider=provider, tools=registry, system_prompt="test")
        )
        out = loop.run(text="can i install now", lang="EN", user_id="u1")["result"]
        self.assertEqual(out.decision, "direct_answer")
        self.assertGreaterEqual(out.confidence, 0.8)
        self.assertTrue(out.tool_needed)

    def test_react_loop_escalation(self):
        provider = _FakeProvider(
            ['{"action":"final","decision":"escalate_human","answer":"Connecting to human","confidence":0.9}']
        )
        registry = AgentToolRegistry(HybridRetriever(provider=None), SimpleReranker(provider=None))
        loop = ReActAgentLoop(
            AgentLoopDependencies(provider=provider, tools=registry, system_prompt="test")
        )
        out = loop.run(text="need live agent", lang="EN", user_id="u2")["result"]
        self.assertEqual(out.decision, "escalate_human")
        self.assertTrue(out.escalate_needed)

    def test_plain_text_response_becomes_clarifying_question(self):
        provider = _FakeProvider(
            ["You can email support at support@kommu.ai and engineering@kommu.ai for urgent fixes."]
        )
        registry = AgentToolRegistry(HybridRetriever(provider=None), SimpleReranker(provider=None))
        loop = ReActAgentLoop(
            AgentLoopDependencies(provider=provider, tools=registry, system_prompt="test")
        )
        out = loop.run(text="How to contact support?", lang="EN", user_id="u3")["result"]
        self.assertEqual(out.decision, "clarifying_question")
        self.assertLessEqual(out.confidence, 0.55)

    def test_direct_answer_with_sources_is_allowed(self):
        provider = _FakeProvider(
            [
                '{"action":"final","decision":"direct_answer","answer":"Install by appointment.","confidence":0.9,"source_ids":["intent:install_booking"]}',
            ]
        )
        registry = AgentToolRegistry(HybridRetriever(provider=None), SimpleReranker(provider=None))
        loop = ReActAgentLoop(
            AgentLoopDependencies(provider=provider, tools=registry, system_prompt="test")
        )
        out = loop.run(text="Can I walk in for install?", lang="EN", user_id="u4")["result"]
        self.assertEqual(out.decision, "direct_answer")
        self.assertGreaterEqual(out.confidence, 0.8)


    def test_clarify_hedge_triggers_repair(self):
        class _RepairProvider:
            def __init__(self):
                self.calls = 0

            def chat_messages(self, messages, temperature=0.2, max_tokens=1200):
                self.calls += 1
                if self.calls == 1:
                    return (
                        '{"action":"final","decision":"clarifying_question",'
                        '"answer":"I want to make sure I give you accurate info. What car?",'
                        '"confidence":0.5}'
                    )
                return (
                    '{"action":"final","decision":"clarifying_question",'
                    '"question":"What car brand and model do you drive?",'
                    '"confidence":0.55}'
                )

        prov = _RepairProvider()
        registry = AgentToolRegistry(HybridRetriever(provider=None), SimpleReranker(provider=None))
        loop = ReActAgentLoop(AgentLoopDependencies(provider=prov, tools=registry, system_prompt="test"))
        out = loop.run(text="help", lang="EN", user_id="u_hedge")["result"]
        self.assertEqual(out.decision, "clarifying_question")
        self.assertNotIn("accurate info", out.answer.lower())
        self.assertIn("car", out.answer.lower())
        self.assertEqual(out.metadata.get("clarify_sanitize"), "clarify_repair")


if __name__ == "__main__":
    unittest.main()

