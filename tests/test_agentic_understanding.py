import unittest

from support_runtime.agent_loop import AgentLoopDependencies, ReActAgentLoop
from support_runtime.agent_tools import AgentToolRegistry
from support_runtime.retrieval import HybridRetriever, SimpleReranker


class _Provider:
    def chat(self, *_args, **_kwargs):
        return (
            '{"action":"final","decision":"direct_answer","answer":"Understood.",'
            '"confidence":0.8,"source_ids":["intent:test"]}'
        )

    def chat_messages(self, messages, **_kwargs):
        return (
            '{"action":"final","decision":"direct_answer","answer":"Understood.",'
            '"confidence":0.8,"source_ids":["intent:test"]}'
        )


class AgenticUnderstandingTests(unittest.TestCase):
    def test_agent_loop_direct_answer_path(self):
        loop = ReActAgentLoop(
            AgentLoopDependencies(
                provider=_Provider(),
                tools=AgentToolRegistry(HybridRetriever(provider=None), SimpleReranker(provider=None)),
                system_prompt="test",
            )
        )
        out = loop.run(text="myvi h 2022 can it be supported?", lang="EN", user_id="u1")["result"]
        self.assertEqual(out.decision, "direct_answer")
        self.assertEqual(out.capability_used, "react_agent_loop")


if __name__ == "__main__":
    unittest.main()
