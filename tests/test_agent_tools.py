import unittest

from support_runtime.agent_tools import AgentToolRegistry
from support_runtime.retrieval import HybridRetriever, SimpleReranker


class AgentToolsTests(unittest.TestCase):
    def test_registry_contains_required_tools(self):
        reg = AgentToolRegistry(HybridRetriever(provider=None), SimpleReranker(provider=None))
        names = {x["name"] for x in reg.list_schemas()}
        self.assertTrue(
            {
                "search_faq",
                "search_web",
                "search_kommu_support",
                "search_bukapilot",
                "read_bukapilot_file",
                "lookup_warranty",
                "lookup_backlog",
                "log_backlog",
                "escalate_to_human",
            }.issubset(names)
        )

    def test_unknown_tool_fails_safely(self):
        reg = AgentToolRegistry(HybridRetriever(provider=None), SimpleReranker(provider=None))
        out = reg.call("does_not_exist", {})
        self.assertFalse(out["ok"])
        self.assertIn("unknown_tool", out["error"])


if __name__ == "__main__":
    unittest.main()

