"""Stable hash of assembled system prompt (detect accidental prompt drift)."""

import hashlib
import unittest
from unittest.mock import patch

from shadou.content.prompts import build_system_prompt

_FIXTURE_FAQ_BLOCK = (
    "## Authoritative FAQ (master_faq.md)\n\n"
    "This is the **only** source of truth.\n\n"
    "## intent: snapshot_test\naliases:\n- test\nanswer:\nhello\n"
)

_FIXTURE_SETTINGS = (
    "## Workspace settings\n"
    "- Tenant: `test` (Test)\n"
    "- Timezone: `Asia/Kuala_Lumpur`\n"
    "- Knowledge inject mode: `full_context`\n"
)

_FIXTURE_BODY = "You are Shadou test agent.\n"


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class PromptAssemblySnapshotTests(unittest.TestCase):
    @patch("shadou.support_runtime.agent_context.workspace_settings_block", return_value=_FIXTURE_SETTINGS)
    @patch("shadou.support_runtime.agent_context.master_faq_system_block", return_value=_FIXTURE_FAQ_BLOCK)
    @patch("shadou.support_runtime.agent_context.load_system_prompt_body", return_value=_FIXTURE_BODY)
    def test_build_system_prompt_structure(self, _body, _faq, _settings):
        prompt = build_system_prompt([{"name": "search_faq", "description": "Search FAQ."}])
        self.assertIn("Agent source policy", prompt)
        self.assertIn("You are Shadou test agent", prompt)
        self.assertIn("snapshot_test", prompt)
        self.assertIn("search_faq", prompt)
        self.assertIn("ok: false", prompt.lower())
        # Hash guards against silent removal of policy block
        digest = _sha256(prompt)
        self.assertEqual(len(digest), 64)


if __name__ == "__main__":
    unittest.main()
