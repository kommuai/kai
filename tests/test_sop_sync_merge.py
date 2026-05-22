import tempfile
import unittest
from unittest.mock import patch

from kai.core.faq_markdown import parse_master_faq_schema
from kai.core.sop_sync_merge import merge_schemas, render_merged_schema_to_markdown, sync_sop_regions


class SopSyncMergeTests(unittest.TestCase):
    def test_merge_google_wins_intent_answer_and_unions_aliases(self):
        local = {
            "intents": [{"intent_id": "test_drive", "aliases": ["test drive", "demo"], "answer": "Local answer"}],
            "workflows": [],
            "data": [],
            "dynamic": [],
        }
        google = {
            "intents": [{"intent_id": "test_drive", "aliases": ["book test drive"], "answer": "Google answer"}],
            "workflows": [],
            "data": [],
            "dynamic": [],
        }
        out = merge_schemas(local, google)
        intent = out["intents"][0]
        self.assertEqual(intent["answer"], "Google answer")
        self.assertEqual(intent["aliases"], ["book test drive", "test drive", "demo"])

    def test_merge_dynamic_google_field_wins(self):
        local = {
            "intents": [],
            "workflows": [],
            "data": [],
            "dynamic": [{"name": "batch_status", "fields": {"batch": "4", "valid_until": "2026-04-30", "priority": "5"}}],
        }
        google = {
            "intents": [],
            "workflows": [],
            "data": [],
            "dynamic": [{"name": "batch_status", "fields": {"status": "assembling", "valid_until": "2026-05-31", "priority": "10"}}],
        }
        out = merge_schemas(local, google)
        dyn = out["dynamic"][0]
        self.assertEqual(dyn["fields"]["valid_until"], "2026-05-31")
        self.assertEqual(dyn["fields"]["priority"], "10")
        self.assertEqual(dyn["fields"]["batch"], "4")
        self.assertEqual(dyn["fields"]["status"], "assembling")

    def test_render_round_trip_parseable(self):
        merged = {
            "intents": [{"intent_id": "foo", "aliases": ["a1"], "answer": "A"}],
            "workflows": [{"workflow_id": "wf", "steps": ["s1", "s2"]}],
            "data": [{"name": "bank", "fields": {"name": "Kommu"}}],
            "dynamic": [{"name": "batch_status", "fields": {"batch": "4", "priority": "10"}}],
        }
        md = render_merged_schema_to_markdown(merged)
        parsed = parse_master_faq_schema(md)
        self.assertEqual(parsed["intents"][0]["intent_id"], "foo")
        self.assertEqual(parsed["workflows"][0]["workflow_id"], "wf")
        self.assertEqual(parsed["data"][0]["name"], "bank")
        self.assertEqual(parsed["dynamic"][0]["name"], "batch_status")

    @patch("kai.core.sop_sync_merge.push_master_faq_to_google_doc", return_value={"ok": True})
    @patch("kai.core.sop_sync_merge.pull_google_region")
    @patch("kai.core.sop_sync_merge.read_local_region")
    def test_sync_sop_regions_updates_local_and_calls_writeback(self, local_mock, google_mock, writeback_mock):
        local_mock.return_value = (
            "## intent: t\naliases:\n- test drive\nanswer:\nLocal\n"
        )
        google_mock.return_value = (
            "## intent: t\naliases:\n- book test drive\nanswer:\nGoogle\n"
        )
        with tempfile.TemporaryDirectory() as td:
            faq_path = f"{td}/master_faq.md"
            with open(faq_path, "w", encoding="utf-8") as f:
                f.write("before\n<!-- sop-sync:start -->\n\n<!-- sop-sync:end -->\nafter\n")
            from pathlib import Path

            state_path = Path(td) / "sop_sync_state.json"
            with patch("kai.core.sop_sync_merge._master_faq_path", return_value=Path(faq_path)), patch(
                "kai.core.sop_sync_merge._state_path", return_value=state_path
            ):
                out = sync_sop_regions()
            self.assertTrue(out["ok"])
            updated = open(faq_path, "r", encoding="utf-8").read()
            self.assertIn("Google", updated)
            self.assertIn("book test drive", updated)
            writeback_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()
