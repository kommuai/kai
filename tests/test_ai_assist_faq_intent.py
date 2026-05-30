"""AI Assist — faq_intent patches merge one intent at a time."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "studio" / "backend"))

from ai_assist_core import apply_patch_item, preview_patches, validate_ai_assist_patches  # noqa: E402
from fastapi import HTTPException  # noqa: E402


class AiAssistFaqIntentTests(unittest.TestCase):
    def test_faq_intent_patch_updates_one_section(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            (home / "knowledge").mkdir()
            faq = (
                "## intent: warranty\n"
                "aliases:\n- warranty\n"
                "answer:\nOld text\n\n"
                "## intent: other\n"
                "answer:\nKeep\n"
            )
            (home / "knowledge" / "master_faq.md").write_text(faq, encoding="utf-8")

            result = apply_patch_item(
                home,
                {
                    "type": "faq_intent",
                    "intent_id": "warranty",
                    "content": "aliases:\n- warranty\nanswer:\nPlug and play.\n",
                },
            )
            self.assertIsNotNone(result)
            assert result is not None
            self.assertEqual(result.get("intent_id"), "warranty")
            updated = (home / "knowledge" / "master_faq.md").read_text(encoding="utf-8")
            self.assertIn("Plug and play.", updated)
            self.assertIn("Keep", updated)
            self.assertNotIn("Old text", updated)

    def test_validate_rejects_full_faq_config_file(self) -> None:
        with self.assertRaises(HTTPException) as ctx:
            validate_ai_assist_patches(
                [{"type": "config_file", "file": "faq", "content": "## intent: x\nanswer:\ny\n"}]
            )
        self.assertIn("faq_intent", str(ctx.exception.detail))

    def test_preview_faq_intent_small_diff(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            (home / "knowledge").mkdir()
            (home / "knowledge" / "master_faq.md").write_text(
                "## intent: a\nanswer:\n1\n\n## intent: b\nanswer:\n2\n",
                encoding="utf-8",
            )
            previews = preview_patches(
                home,
                [
                    {
                        "type": "faq_intent",
                        "intent_id": "a",
                        "content": "answer:\n9\n",
                    }
                ],
            )
            self.assertEqual(len(previews), 1)
            self.assertEqual(previews[0].get("intent_id"), "a")
            self.assertIn("+9", previews[0]["diff"])
            self.assertIn("-1", previews[0]["diff"])


if __name__ == "__main__":
    unittest.main()
