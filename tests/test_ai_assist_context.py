"""AI Assist build_context — config files share a 128k context limit."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "studio" / "backend"))

from ai_assist_core import build_context  # noqa: E402


class AiAssistContextTests(unittest.TestCase):
    def test_faq_not_truncated_at_legacy_8k_limit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            (home / "knowledge").mkdir()
            long_faq = ("x" * 9000) + "\n## intent: vehicle_manufacturer_warranty\nplug and play\n"
            (home / "knowledge" / "master_faq.md").write_text(long_faq, encoding="utf-8")
            (home / "workspace.yaml").write_text("version: '2'\n", encoding="utf-8")
            (home / "system_prompt.md").write_text("rules\n", encoding="utf-8")

            ctx = build_context(home)
            self.assertIn("vehicle_manufacturer_warranty", ctx)
            self.assertNotIn("[truncated", ctx)

    def test_workspace_not_truncated_at_legacy_8k_limit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            (home / "knowledge").mkdir()
            (home / "knowledge" / "master_faq.md").write_text("faq\n", encoding="utf-8")
            (home / "system_prompt.md").write_text("rules\n", encoding="utf-8")
            long_workspace = ("x" * 9000) + "\nversion: '2'\n"
            (home / "workspace.yaml").write_text(long_workspace, encoding="utf-8")

            ctx = build_context(home)
            self.assertIn("version: '2'", ctx)
            self.assertNotIn("[truncated", ctx)


if __name__ == "__main__":
    unittest.main()
