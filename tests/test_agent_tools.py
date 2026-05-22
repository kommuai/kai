import unittest
from unittest.mock import patch, Mock

from kai.support_runtime.agent_tools import AgentToolRegistry
from kai.support_runtime.retrieval import HybridRetriever, SimpleReranker


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
                "create_visitor_pass",
            }.issubset(names)
        )

    def test_unknown_tool_fails_safely(self):
        reg = AgentToolRegistry(HybridRetriever(provider=None), SimpleReranker(provider=None))
        out = reg.call("does_not_exist", {})
        self.assertFalse(out["ok"])
        self.assertIn("unknown_tool", out["error"])

    @patch("kai.support_runtime.agent_tools.os.path.isfile", return_value=True)
    @patch("kai.support_runtime.agent_tools.subprocess.run")
    def test_create_visitor_pass_tool_success(self, mock_run: Mock, _mock_isfile: Mock):
        mock_run.return_value = Mock(
            returncode=0,
            stdout='{"ok": true, "visitor_pass_link": "https://example.com/pass", "visitor_name": "A", "visitor_phone": "0123456789", "visitor_id": "1", "status": "Approved", "visit_date": "2026-03-28", "visit_time": "18:30"}',
            stderr="",
        )
        reg = AgentToolRegistry(HybridRetriever(provider=None), SimpleReranker(provider=None))
        out = reg.call("create_visitor_pass", {"visit_date": "2026-03-28", "visit_time": "18:30"})
        self.assertTrue(out["ok"])
        self.assertEqual(out["visitor_pass_link"], "https://example.com/pass")

    @patch("kai.support_runtime.agent_tools.os.path.isfile", return_value=True)
    @patch("kai.support_runtime.agent_tools.subprocess.run")
    def test_create_visitor_pass_tool_defaults_to_now_when_date_time_missing(
        self, mock_run: Mock, _mock_isfile: Mock
    ):
        mock_run.return_value = Mock(
            returncode=0,
            stdout='{"ok": true, "visitor_pass_link": "https://example.com/pass2", "visitor_name": "B", "visitor_phone": "01111111111", "visitor_id": "2", "status": "Approved"}',
            stderr="",
        )
        reg = AgentToolRegistry(HybridRetriever(provider=None), SimpleReranker(provider=None))
        out = reg.call("create_visitor_pass", {})
        self.assertTrue(out["ok"])
        called_cmd = mock_run.call_args.kwargs.get("args") or mock_run.call_args.args[0]
        self.assertNotIn("--date", called_cmd)
        self.assertNotIn("--time", called_cmd)

    @patch("kai.support_runtime.agent_tools.os.path.isfile", return_value=True)
    @patch("kai.support_runtime.agent_tools.subprocess.run")
    def test_create_visitor_pass_tool_failure(self, mock_run: Mock, _mock_isfile: Mock):
        mock_run.return_value = Mock(
            returncode=1,
            stdout='{"ok": false, "error": "bad_input"}',
            stderr="",
        )
        reg = AgentToolRegistry(HybridRetriever(provider=None), SimpleReranker(provider=None))
        out = reg.call("create_visitor_pass", {"visit_date": "bad", "visit_time": "xx"})
        self.assertFalse(out["ok"])
        self.assertIn("error", out)


if __name__ == "__main__":
    unittest.main()

