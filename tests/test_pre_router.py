import unittest

from kai.services.container import kai_service, support_runtime_service
from kai.lib.session_state import reset_memory


class PreRouterTests(unittest.TestCase):
    def test_la_handover_via_pre_router(self):
        uid = "test_pre_la"
        reset_memory(uid)
        data = {"content": "LA", "phone_number": uid}
        early = kai_service.pre_router(dict(data))
        self.assertIsNotNone(early)
        self.assertEqual(early.get("type"), "handover")
        self.assertEqual(early.get("next_state"), "human")

    def test_plain_text_continues_to_support_runtime(self):
        uid = "test_pre_continue"
        reset_memory(uid)
        data = {"content": "what is the price?", "phone_number": uid}
        early = kai_service.pre_router(dict(data))
        self.assertIsNone(early)
        support_runtime_service.startup()
        out = support_runtime_service.execute(text=data["content"], lang="EN", user_id=uid)
        self.assertIn(out.decision, {"direct_answer", "clarifying_question", "escalate_human"})


if __name__ == "__main__":
    unittest.main()
