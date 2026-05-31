"""LLM usage recording — tenant slug from SHADOU_HOME."""
from __future__ import annotations

import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from shadou.lib.deepseek_pricing import TokenUsage
from shadou.lib.llm_usage_record import record_openai_usage, resolve_usage_tenant_slug


class LlmUsageRecordTests(unittest.TestCase):
    def test_resolve_tenant_slug_from_shadou_home_path(self) -> None:
        with patch.dict(os.environ, {"SHADOU_HOME": "/home/ting/workspace/shadou-tenant-kommu"}, clear=False):
            self.assertEqual(resolve_usage_tenant_slug(), "kommu")

    def test_record_openai_usage_uses_shadou_home_slug(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_dir = Path(tmp)
            with patch.dict(
                os.environ,
                {"SHADOU_HOME": "/data/shadou-tenant-acme", "SHADOU_ADMIN_DB_DIR": str(db_dir)},
                clear=False,
            ):
                # Create admin.db like Studio does
                from shadou.lib.llm_usage_record import _ensure_table

                with sqlite3.connect(db_dir / "admin.db") as conn:
                    _ensure_table(conn)
                    conn.commit()

                usage = {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}
                row = record_openai_usage(model="deepseek-v4-flash", usage=usage, source="engine_chat")
                self.assertIsNotNone(row)
                self.assertEqual(row["tenant_slug"], "acme")

                with sqlite3.connect(db_dir / "admin.db") as conn:
                    slug = conn.execute("SELECT tenant_slug FROM llm_usage_events").fetchone()[0]
                self.assertEqual(slug, "acme")


if __name__ == "__main__":
    unittest.main()
