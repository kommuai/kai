import unittest
from uuid import uuid4

from shadou.services.shadou_service import strip_bold_markdown_wrapping_around_urls
from shadou.support_runtime.compiler import compile_canonical_knowledge
from shadou.support_runtime.service import SupportRuntimeService


class SupportRuntimeTests(unittest.TestCase):
    def test_compiler_loads_intents(self):
        counts = compile_canonical_knowledge()
        self.assertGreater(counts["intents"], 0)
        self.assertGreater(counts["chunks"], 0)

    def test_service_returns_structured_decision(self):
        svc = SupportRuntimeService()
        svc.startup()
        out = svc.execute("I want order status", lang="EN")
        self.assertIsInstance(out.decision, str)
        self.assertIsInstance(out.answer, str)

    def test_generic_question_runs_agent_loop(self):
        svc = SupportRuntimeService()
        svc.startup()
        out = svc.execute("What are your office hours?", lang="EN", user_id=f"q_{uuid4().hex[:8]}")
        self.assertEqual(out.capability_used, "react_agent_loop")
        self.assertTrue(out.answer.strip())

    def test_vehicle_question_runs_agent_loop_without_crash(self):
        svc = SupportRuntimeService()
        svc.startup()
        out = svc.execute("Is BMW 3 series supported?", lang="EN", user_id="vs_u1")
        self.assertEqual(out.capability_used, "react_agent_loop")
        self.assertTrue(out.answer.strip())

    def test_strip_bold_markdown_wrapping_around_urls(self):
        raw = "Link: **https://example.com/path** (open)"
        self.assertEqual(
            strip_bold_markdown_wrapping_around_urls(raw),
            "Link: https://example.com/path (open)",
        )


if __name__ == "__main__":
    unittest.main()
