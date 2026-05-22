import unittest
from unittest.mock import patch

from kai.support_runtime.agent_tools import AgentToolRegistry
from kai.support_runtime.retrieval import HybridRetriever, SimpleReranker


class LogBacklogReadinessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.reg = AgentToolRegistry(HybridRetriever(provider=None), SimpleReranker(provider=None))

    def test_log_backlog_refuses_when_device_unknown(self):
        out = self.reg.log_backlog(
            issue="KA2 error 1003 logs missing",
            device="Unknown",
            car="Unknown",
        )
        self.assertFalse(out["ok"])
        self.assertEqual(out["error"], "log_backlog_not_ready_missing_device_car")

    def test_log_backlog_refuses_when_car_unknown(self):
        out = self.reg.log_backlog(
            issue="KA2 error 1003 logs missing",
            device="KA2",
            car="Unknown",
        )
        self.assertFalse(out["ok"])
        self.assertEqual(out["error"], "log_backlog_not_ready_missing_device_car")

    @patch(
        "kai.support_runtime.agent_tools.deepseek_chat_completion",
        return_value='{"problem_description":"DEEPSEEK PROBLEM","reproduction_steps":"Step 1 then Step 2."}',
    )
    @patch("kai.support_runtime.agent_tools.append_backlog_issue", return_value={"ok": True, "updatedRange": "A1:E1"})
    def test_log_backlog_calls_append_when_ready(self, append_mock, _deepseek_mock):
        out = self.reg.log_backlog(
            issue="KA2 error 1003 logs missing",
            device="KA2",
            car="Honda City 2021",
        )
        self.assertTrue(out["ok"])
        append_mock.assert_called_once()
        kwargs = append_mock.call_args.kwargs
        self.assertEqual(kwargs.get("device"), "KA2")
        self.assertEqual(kwargs.get("car"), "Honda City 2021")
        self.assertEqual(kwargs.get("issue_description"), "DEEPSEEK PROBLEM")
        self.assertEqual(kwargs.get("reproduction_steps"), "Step 1 then Step 2.")


if __name__ == "__main__":
    unittest.main()

