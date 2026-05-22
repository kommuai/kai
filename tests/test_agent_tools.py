import unittest
from unittest.mock import patch, Mock

from kai.support_runtime.agent_tools import AgentToolRegistry
from kai.support_runtime.retrieval import HybridRetriever, SimpleReranker
from kai.workspace.tools_config import reload_tools_config


class AgentToolsTests(unittest.TestCase):
    def setUp(self):
        reload_tools_config()

    def test_registry_contains_kommu_profile_tools(self):
        reg = AgentToolRegistry(HybridRetriever(provider=None), SimpleReranker(provider=None))
        names = {x["name"] for x in reg.list_schemas()}
        self.assertTrue(
            {
                "search_faq",
                "search_kommu_support",
                "lookup_warranty",
                "create_visitor_pass",
            }.issubset(names)
        )

    def test_unknown_tool_fails_safely(self):
        reg = AgentToolRegistry(HybridRetriever(provider=None), SimpleReranker(provider=None))
        out = reg.call("does_not_exist", {})
        self.assertFalse(out["ok"])
        self.assertIn("unknown_tool", out["error"])

    @patch("kai.support_runtime.tools.registry.run_plugin_tool")
    def test_create_visitor_pass_plugin_success(self, mock_plugin: Mock):
        mock_plugin.return_value = {
            "ok": True,
            "visitor_pass_link": "https://example.com/pass",
            "visitor_name": "A",
            "visitor_phone": "0123456789",
            "visitor_id": "1",
            "status": "Approved",
            "visit_date": "2026-03-28",
            "visit_time": "18:30",
        }
        reg = AgentToolRegistry(HybridRetriever(provider=None), SimpleReranker(provider=None))
        out = reg.call("create_visitor_pass", {"visit_date": "2026-03-28", "visit_time": "18:30"})
        self.assertTrue(out["ok"])
        self.assertEqual(out["visitor_pass_link"], "https://example.com/pass")
        mock_plugin.assert_called_once()

    @patch("kai.support_runtime.tools.registry.run_plugin_tool")
    def test_create_visitor_pass_plugin_failure(self, mock_plugin: Mock):
        mock_plugin.return_value = {"ok": False, "error": "bad_input"}
        reg = AgentToolRegistry(HybridRetriever(provider=None), SimpleReranker(provider=None))
        out = reg.call("create_visitor_pass", {})
        self.assertFalse(out["ok"])


if __name__ == "__main__":
    unittest.main()
