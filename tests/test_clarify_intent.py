"""Unit tests for intent-aware clarify fallback and chitchat detection.

These guard against the regression seen in the chat history where the bot
asked "Reply with your car brand, model, and year..." for office/pricing/
warranty/greeting messages, pushing users toward `LA`.
"""

from __future__ import annotations

import unittest

from support_runtime.agent_loop import _looks_like_chitchat
from support_runtime.clarify_intent import pick_clarify_for_intent


class ClarifyIntentPickerTests(unittest.TestCase):
    def test_office_query_routes_to_office_clarify(self):
        out = pick_clarify_for_intent("is your office open today?")
        self.assertIn("office", out.lower())
        self.assertNotIn("car brand", out.lower())

    def test_pricing_query_routes_to_pricing_clarify(self):
        out = pick_clarify_for_intent("how much for kommu?")
        self.assertIn("rm4,999", out.lower())
        self.assertNotIn("dongle", out.lower())

    def test_warranty_query_routes_to_dongle_request(self):
        out = pick_clarify_for_intent("is my device still under warranty")
        self.assertIn("dongle", out.lower())

    def test_install_query_routes_to_install_clarify(self):
        out = pick_clarify_for_intent("how to self install?")
        self.assertIn("install", out.lower())

    def test_qr_query_routes_to_visitor_pass_clarify(self):
        out = pick_clarify_for_intent("can i have qr access link for tomorrow")
        self.assertTrue("qr" in out.lower() or "visit" in out.lower())

    def test_vehicle_query_routes_to_acc_lka_question(self):
        out = pick_clarify_for_intent("Mazda CX-5")
        self.assertIn("acc", out.lower())
        self.assertIn("lka", out.lower())

    def test_supported_list_question_does_not_ask_car_brand(self):
        out = pick_clarify_for_intent("list of supported cars please")
        self.assertIn("kommu.ai/support", out.lower())

    def test_unknown_query_falls_back_to_friendly_menu(self):
        out = pick_clarify_for_intent("hello there what can you do")
        # menu mentions multiple choices, not a single car/dongle interrogation
        self.assertNotIn("dongle", out.lower())
        self.assertIn("?", out)

    def test_bm_language_returns_malay_phrasing(self):
        out = pick_clarify_for_intent("berapa harga", lang="BM")
        self.assertTrue(any(w in out.lower() for w in ("harga", "deposit", "rm4,999")))


class ChitchatDetectionTests(unittest.TestCase):
    def test_test_message_treated_as_chitchat(self):
        self.assertTrue(_looks_like_chitchat("Test"))
        self.assertTrue(_looks_like_chitchat("testing"))

    def test_howdy_and_hai_chitchat(self):
        self.assertTrue(_looks_like_chitchat("Howdy"))
        self.assertTrue(_looks_like_chitchat("hai bos"))

    def test_emoji_only_chitchat(self):
        self.assertTrue(_looks_like_chitchat("👍"))

    def test_long_question_is_not_chitchat(self):
        self.assertFalse(_looks_like_chitchat("Hi, can you tell me the price for Perodua Alza AV 2024 including installation?"))


if __name__ == "__main__":
    unittest.main()
