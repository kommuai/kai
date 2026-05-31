import unittest

from shadou.services.container import support_runtime_service


class DiagnosticAndFaqLoopTests(unittest.TestCase):
    def test_unknown_product_diagnostic_escalates(self):
        support_runtime_service.startup()
        out = support_runtime_service.execute("my device has error 1003", lang="EN", user_id="diag_u1")
        self.assertEqual(out.capability_used, "react_agent_loop")
        self.assertTrue(out.answer.strip())
        self.assertIsInstance(out.decision, str)


if __name__ == "__main__":
    unittest.main()
