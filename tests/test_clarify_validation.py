import unittest

from support_runtime.clarify_validation import (
    clarify_candidate_from_parsed,
    is_valid_clarifying_text,
    last_question_span,
)


class ClarifyValidationTests(unittest.TestCase):
    def test_valid_simple_question(self):
        ok, _ = is_valid_clarifying_text("What car brand and model do you drive?")
        self.assertTrue(ok)

    def test_rejects_no_question_mark(self):
        ok, reason = is_valid_clarifying_text("Tell me your car brand")
        self.assertFalse(ok)
        self.assertEqual(reason, "no_question_mark")

    def test_rejects_hedge_accurate_info(self):
        bad = (
            "I want to make sure I give you accurate info. Could you share one more detail "
            "so I can confirm the facts? What car?"
        )
        ok, reason = is_valid_clarifying_text(bad)
        self.assertFalse(ok)
        self.assertEqual(reason, "hedge")

    def test_candidate_prefers_question_field(self):
        p = {
            "question": "What year?",
            "answer": "ignore me",
        }
        self.assertEqual(clarify_candidate_from_parsed(p), "What year?")

    def test_last_question_span_strips_preamble(self):
        text = "I want to be helpful. What is your dongle ID?"
        self.assertEqual(last_question_span(text), "What is your dongle ID?")


if __name__ == "__main__":
    unittest.main()
