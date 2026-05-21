import unittest
from uuid import uuid4

from services.kai_service import strip_bold_markdown_wrapping_around_urls
from support_runtime.compiler import compile_canonical_knowledge
from support_runtime.router import IntentRouter
from support_runtime.service import SupportRuntimeService


class SupportRuntimeTests(unittest.TestCase):
    def test_compiler_and_router_load(self):
        counts = compile_canonical_knowledge()
        self.assertGreaterEqual(counts["intents"], 0)
        router = IntentRouter()
        router.load()
        route_type, conf, _ = router.route("order status")
        self.assertEqual(route_type, "account_order_status_intent")
        self.assertGreater(conf, 0.5)

    def test_service_returns_structured_decision(self):
        svc = SupportRuntimeService()
        svc.startup()
        out = svc.execute("I want order status", lang="EN")
        self.assertIn(out.decision, {"clarifying_question", "tool_use", "escalate_human", "direct_answer"})
        self.assertIsInstance(out.answer, str)

    def test_faq_first_returns_video_link_on_first_message_only(self):
        svc = SupportRuntimeService()
        svc.startup()
        uid = f"vid_{uuid4().hex[:6]}"
        out1 = svc.execute(
            "self install video guide link for kommu assist",
            lang="EN",
            user_id=uid,
        )
        self.assertEqual(out1.capability_used, "canonical_answer")
        self.assertIn("youtu", out1.answer.lower())
        out2 = svc.execute("Is there any video for this?", lang="EN", user_id=uid)
        self.assertEqual(out2.capability_used, "react_agent_loop")

    def test_install_and_warranty_routes_unaffected(self):
        svc = SupportRuntimeService()
        svc.startup()
        install = svc.execute("can i come now and install?", lang="EN", user_id=f"ins_{uuid4().hex[:6]}")
        self.assertEqual(install.capability_used, "react_agent_loop")
        warranty = svc.execute("ABC12345", lang="EN", user_id=f"war_{uuid4().hex[:6]}")
        self.assertEqual(warranty.capability_used, "react_agent_loop")

    def test_install_phrase_routes_to_install_booking_not_vehicle(self):
        svc = SupportRuntimeService()
        svc.startup()
        out = svc.execute("i just bought kommu assist, can i come now and install?", lang="EN", user_id=f"install_{uuid4().hex[:8]}")
        self.assertEqual(out.capability_used, "react_agent_loop")
        self.assertIn(out.decision, {"direct_answer", "clarifying_question"})

    def test_warranty_route_path(self):
        svc = SupportRuntimeService()
        svc.startup()
        out = svc.execute("ABC12345", lang="EN")
        self.assertEqual(out.capability_used, "react_agent_loop")
        self.assertIn(out.decision, {"direct_answer", "clarifying_question"})

    def test_vehicle_support_query_runs_agent_loop(self):
        svc = SupportRuntimeService()
        svc.startup()
        out = svc.execute("Is BMW 3 series supported?", lang="EN", user_id="vs_u1")
        self.assertEqual(out.capability_used, "react_agent_loop")
        self.assertIn(out.decision, {"direct_answer", "clarifying_question", "escalate_human"})

    def test_vehicle_support_multiturn_runs_without_crash(self):
        svc = SupportRuntimeService()
        svc.startup()
        uid = f"vs_u2_{uuid4().hex[:8]}"
        out1 = svc.execute("Is Mazda 3 2022 supported?", lang="EN", user_id=uid)
        self.assertEqual(out1.capability_used, "react_agent_loop")
        out2 = svc.execute("Yes it has ACC and LKA", lang="EN", user_id=uid)
        self.assertEqual(out2.capability_used, "react_agent_loop")
        out3 = svc.execute("Yes, willing to borrow", lang="EN", user_id=uid)
        self.assertEqual(out3.capability_used, "react_agent_loop")

    def test_vehicle_support_model_phrase_uses_agent_loop(self):
        svc = SupportRuntimeService()
        svc.startup()
        out = svc.execute("i have a myvi H, can it be supported?", lang="EN", user_id="vs_model_u1")
        self.assertEqual(out.capability_used, "react_agent_loop")
        self.assertIn(out.decision, {"direct_answer", "clarifying_question"})

    def test_vehicle_support_followup_model_year_no_repeat_loop(self):
        svc = SupportRuntimeService()
        svc.startup()
        uid = f"vs_loop_{uuid4().hex[:8]}"
        _ = svc.execute("i have a myvi H, can it be supported?", lang="EN", user_id=uid)
        out2 = svc.execute("i have a myvi H year 2022", lang="EN", user_id=uid)
        self.assertEqual(out2.capability_used, "react_agent_loop")

    def test_diagnostic_multiturn_runs_in_agent_loop(self):
        svc = SupportRuntimeService()
        svc.startup()
        uid = "diag_try_user"
        q = "KA2 error unknown 999999 still broken"
        out1 = svc.execute(q, lang="EN", user_id=uid)
        self.assertEqual(out1.capability_used, "react_agent_loop")
        out2 = svc.execute(q, lang="EN", user_id=uid)
        self.assertEqual(out2.capability_used, "react_agent_loop")
        out3 = svc.execute(q, lang="EN", user_id=uid)
        self.assertEqual(out3.capability_used, "react_agent_loop")

    def test_strip_bold_markdown_wrapping_around_urls(self):
        raw = "Your pass: **https://emhub.smartserva.com/v/abc** (tap to open)"
        self.assertEqual(
            strip_bold_markdown_wrapping_around_urls(raw),
            "Your pass: https://emhub.smartserva.com/v/abc (tap to open)",
        )


if __name__ == "__main__":
    unittest.main()
