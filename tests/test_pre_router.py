import unittest

from services.container import kai_service
from session_state import reset_memory


class PreRouterParityTests(unittest.TestCase):
    def test_handle_equals_pre_then_main_for_plain_text(self):
        uid = "test_parity_plain"
        reset_memory(uid)
        data = {"content": "random query xyz123 no match", "phone_number": uid}
        full = kai_service.handle_agent_message(dict(data))
        reset_memory(uid)
        early = kai_service.pre_router(dict(data))
        self.assertIsNone(early)
        tail = kai_service.main_conversation(dict(data))
        self.assertEqual(full.get("type"), tail.get("type"))
        self.assertEqual(full.get("next_state"), tail.get("next_state"))

    def test_la_handover_matches_full_handle(self):
        uid = "test_parity_ka2"
        reset_memory(uid)
        data = {"content": "LA", "phone_number": uid}
        full = kai_service.handle_agent_message(dict(data))
        reset_memory(uid)
        early = kai_service.pre_router(dict(data))
        self.assertIsNotNone(early)
        self.assertEqual(early.get("type"), "handover")
        self.assertEqual(full.get("type"), early.get("type"))
        self.assertEqual(full.get("next_state"), early.get("next_state"))


if __name__ == "__main__":
    unittest.main()
