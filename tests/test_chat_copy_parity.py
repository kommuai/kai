"""Ensure chat_copy.yaml matches legacy shadou_service constants."""

import unittest

from shadou.content.copy import get_chat_copy

# Strings from tests/fixtures/minimal_workspace/workspace.yaml (generic contract)
_LEGACY = {
    "footer_en": "\n\nFor a live agent, type LA",
    "footer_bm": "\n\nTaip LA untuk ejen",
    "live_agent": ("LA",),
    "handover_live_agent_en": "A live agent will assist you soon. Type *resume* to continue with the bot.",
    "resume_en": "Bot resumed. How can I help?",
    "media_guard_en": "Please describe your issue in text; media is not supported yet.",
}


class ChatCopyParityTests(unittest.TestCase):
    def test_yaml_matches_legacy_strings(self):
        cp = get_chat_copy()
        self.assertEqual(cp.footer_en.strip(), _LEGACY["footer_en"].strip())
        self.assertEqual(cp.footer_bm.strip(), _LEGACY["footer_bm"].strip())
        self.assertEqual(cp.live_agent, _LEGACY["live_agent"])
        self.assertEqual(cp.handover_live_agent_en, _LEGACY["handover_live_agent_en"])
        self.assertEqual(cp.resume_en, _LEGACY["resume_en"])
        self.assertEqual(cp.media_guard_en, _LEGACY["media_guard_en"])
        self.assertEqual(cp.footer_history_threshold, 10)


if __name__ == "__main__":
    unittest.main()
