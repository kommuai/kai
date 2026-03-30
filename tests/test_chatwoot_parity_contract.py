import unittest

from api.v2.agent_message import _process_agent_message_data
from services.container import kai_service
from session_state import reset_memory


class ChatwootParityContractTests(unittest.TestCase):
    def test_handover_trigger_preserved(self):
        uid = "parity_ka1"
        reset_memory(uid)
        out = _process_agent_message_data({"phone_number": uid, "content": "LA"})
        self.assertEqual(out.get("type"), "handover")
        self.assertEqual(out.get("next_state"), "human")
        self.assertEqual(out.get("capability_used"), "pre_router")
        self.assertIn("trace_id", out)
        self.assertIn("latency_ms", out)

    def test_frozen_resume_preserved(self):
        uid = "parity_resume"
        reset_memory(uid)
        _ = kai_service.pre_router({"phone_number": uid, "content": "LA"})
        out = _process_agent_message_data({"phone_number": uid, "content": "resume"})
        self.assertEqual(out.get("type"), "reply")
        self.assertEqual(out.get("next_state"), "bot")
        self.assertEqual(out.get("capability_used"), "pre_router")

    def test_agent_message_envelope_fields_present(self):
        uid = "parity_envelope"
        reset_memory(uid)
        out = _process_agent_message_data({"phone_number": uid, "content": "Can I install today?"})
        self.assertIn("type", out)
        self.assertIn("message", out)
        self.assertIn("next_state", out)
        self.assertIn("trace_id", out)
        self.assertIn("route_mode", out)
        self.assertIn("capability_used", out)
        self.assertIn("latency_ms", out)


if __name__ == "__main__":
    unittest.main()
