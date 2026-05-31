import unittest
from unittest.mock import Mock, patch

from shadou.support_runtime.agent_tools import AgentToolRegistry
from shadou.support_runtime.retrieval import HybridRetriever, SimpleReranker
from shadou.workspace.tools_config import reload_tools_config


class AgentToolsTests(unittest.TestCase):
    def setUp(self) -> None:
        reload_tools_config()

    def test_registry_contains_minimal_profile_tools(self) -> None:
        reg = AgentToolRegistry(HybridRetriever(provider=None), SimpleReranker(provider=None))
        names = {x["name"] for x in reg.list_schemas()}
        self.assertTrue({"search_faq", "search_session_memory", "escalate_to_human"}.issubset(names))

    def test_unknown_tool_fails_safely(self) -> None:
        reg = AgentToolRegistry(HybridRetriever(provider=None), SimpleReranker(provider=None))
        out = reg.call("does_not_exist", {})
        self.assertFalse(out["ok"])
        self.assertIn("unknown_tool", out["error"])

    @patch("shadou.support_runtime.tools.registry.run_plugin_tool")
    def test_plugin_tool_dispatch(self, mock_plugin: Mock) -> None:
        from pathlib import Path

        from tests.conftest import _apply_shadou_home

        minimal = Path(__file__).resolve().parent / "fixtures" / "minimal_workspace"
        _apply_shadou_home(minimal)
        reload_tools_config()
        mock_plugin.return_value = {"ok": True, "echo": "hello"}
        reg = AgentToolRegistry(HybridRetriever(provider=None), SimpleReranker(provider=None))
        out = reg.call("stub_action", {"message": "hello"})
        self.assertTrue(out["ok"])
        self.assertEqual(out["echo"], "hello")
        mock_plugin.assert_called_once()


if __name__ == "__main__":
    unittest.main()
