"""Ensure chat_copy.yaml matches legacy kai_service constants."""

import unittest

from kai.content.copy import get_chat_copy

# Pre-refactor literals (behavior contract)
_LEGACY = {
    "footer_en": "\n\nFor Live Agent, type LA",
    "footer_bm": "\n\nJika anda mahu bercakap dengan ejen yang sedia ada, taip LA",
    "dropoff": "DROPOFF",
    "live_agent": ("LA",),
    "handover_dropoff_en": (
        "Please provide the date and time for the dropoff. Our staff will assist you soon. "
        "Type *resume* to continue with the bot."
    ),
    "handover_live_agent_en": "A live agent will assist you soon. Type *resume* to continue with the bot.",
    "resume_en": "Bot resumed. How can I help?",
    "media_guard_en": (
        "I am a front-line diagnostic AI and do not support image/video/audio analysis yet. "
        "Please describe the issue in text and tell me what car you are driving (brand/model/year)."
    ),
}


class ChatCopyParityTests(unittest.TestCase):
    def test_yaml_matches_legacy_strings(self):
        cp = get_chat_copy()
        self.assertEqual(cp.footer_en, _LEGACY["footer_en"])
        self.assertEqual(cp.footer_bm, _LEGACY["footer_bm"])
        self.assertEqual(cp.dropoff, _LEGACY["dropoff"])
        self.assertEqual(cp.live_agent, _LEGACY["live_agent"])
        self.assertEqual(cp.handover_dropoff_en, _LEGACY["handover_dropoff_en"])
        self.assertEqual(cp.handover_live_agent_en, _LEGACY["handover_live_agent_en"])
        self.assertEqual(cp.resume_en, _LEGACY["resume_en"])
        self.assertEqual(cp.media_guard_en, _LEGACY["media_guard_en"])
        self.assertEqual(cp.footer_history_threshold, 10)


if __name__ == "__main__":
    unittest.main()
