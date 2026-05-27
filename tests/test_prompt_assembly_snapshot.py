"""Stable hash of assembled system prompt (detect accidental prompt drift)."""

import hashlib
import unittest
from unittest.mock import patch

from kai.content.prompts import build_system_prompt

# Frozen at refactor: empty tools + fixture FAQ block
_FIXTURE_FAQ_BLOCK = (
    "## Authoritative FAQ (master_faq.md)\n\n"
    "This is the **only** source of truth for Kommu product, pricing, installation, "
    "partner installers, warranty, office, and policy answers.\n"
    "- Do **not** contradict this document.\n"
    "- For policy/FAQ questions, answer from here first; paraphrase clearly and keep links verbatim.\n"
    "- Read the **full session chat** in the messages below for follow-ups (postcodes, regions, "
    "yes/no, car model already discussed).\n"
    "- **Answer the user's latest question directly**; read full session for follow-ups (e.g. \"I mean KommuAssist\" after install-fee talk = device price from `pricing_followup`).\n"
    "- Use tools only when this FAQ does not cover the request (official vehicle list, dongle "
    "warranty lookup, visitor pass API, bukapilot code, backlog).\n\n"
    "## intent: snapshot_test\naliases:\n- test\nanswer:\nhello\n"
)

_EXPECTED_HASH = "3fb7a7904e73b1190cce97fcf4e433736afd6565307676df1b476aed46518bc2"


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class PromptAssemblySnapshotTests(unittest.TestCase):
    @patch("kai.content.prompts.local_clock_block", return_value="## Current time (ground truth for scheduling)\n- Now: `2000-01-01 12:00` `Saturday` — timezone `Asia/Kuala_Lumpur`\n")
    @patch("kai.content.prompts.master_faq_system_block", return_value=_FIXTURE_FAQ_BLOCK)
    def test_build_system_prompt_hash(self, _faq, _clock):
        prompt = build_system_prompt([{"name": "search_faq", "description": "Search FAQ."}])
        digest = _sha256(prompt)
        self.assertEqual(digest, _EXPECTED_HASH)
        self.assertIn("You are Kai", prompt)
        self.assertIn("snapshot_test", prompt)
        self.assertIn("search_faq", prompt)


if __name__ == "__main__":
    unittest.main()
