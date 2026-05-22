import unittest
from unittest.mock import Mock, patch

from kai.api.v2.agent_message import _process_agent_message_data
from kai.support_runtime.models import RuntimeResult


class ChatwootLiveHandoverTests(unittest.TestCase):
    @patch("kai.api.v2.agent_message.kai_service.pre_router", return_value=None)
    @patch("kai.api.v2.agent_message.support_runtime_service.execute")
    @patch("kai.api.v2.agent_message.enforce_live_agent_handover", return_value=(True, ""))
    @patch("kai.api.v2.agent_message.KAI_CHATWOOT_ENFORCE_LIVE_HANDOVER", "1")
    def test_escalation_applies_live_handover(self, handover_mock, execute_mock, _pre):
        execute_mock.return_value = RuntimeResult(
            decision="escalate_human",
            answer="Escalating now.",
            confidence=0.9,
            escalate_needed=True,
            capability_used="diagnostic_exact_gate",
        )
        out = _process_agent_message_data(
            {"phone_number": "+6000000000", "content": "KA2 error 999", "conversation_id": 123}
        )
        self.assertEqual(out.get("type"), "handover")
        self.assertTrue(out.get("handover_applied"))
        handover_mock.assert_called_once()

    @patch("kai.api.v2.agent_message.kai_service.pre_router", return_value=None)
    @patch("kai.api.v2.agent_message.support_runtime_service.execute")
    @patch("kai.api.v2.agent_message.enforce_live_agent_handover", return_value=(False, "toggle_status_failed:500"))
    @patch("kai.api.v2.agent_message.KAI_CHATWOOT_ENFORCE_LIVE_HANDOVER", "1")
    def test_escalation_fail_closed_when_handover_fails(self, _handover_mock, execute_mock, _pre):
        execute_mock.return_value = RuntimeResult(
            decision="escalate_human",
            answer="Escalating now.",
            confidence=0.9,
            escalate_needed=True,
            capability_used="diagnostic_exact_gate",
            fallback_reason="diagnostic_no_exact_match",
        )
        out = _process_agent_message_data(
            {"phone_number": "+6000000000", "content": "KA2 error 999", "conversation_id": 123}
        )
        self.assertEqual(out.get("type"), "handover_failed")
        self.assertFalse(out.get("handover_applied"))
        self.assertIn("handover_error", out)


if __name__ == "__main__":
    unittest.main()
