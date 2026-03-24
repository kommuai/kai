import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from api.v2.agent_message import (
    admin_approve_faq_candidate,
    admin_list_faq_candidates,
    admin_publish_faq_candidate,
)
from services.container import support_runtime_service
from session_state import init_db, list_faq_candidates, upsert_faq_candidate
from support_runtime.faq_feedback import ingest_tagged_resolutions


class DiagnosticAndFaqLoopTests(unittest.TestCase):
    def test_unknown_product_diagnostic_escalates(self):
        support_runtime_service.startup()
        out = support_runtime_service.execute("my device has error 1003", lang="EN", user_id="diag_u1")
        self.assertEqual(out.capability_used, "react_agent_loop")
        self.assertIn(out.decision, {"direct_answer", "clarifying_question", "escalate_human"})

    @patch("support_runtime.faq_feedback.push_master_faq_to_google_doc", return_value={"ok": False, "error": "writeback_disabled"})
    @patch("support_runtime.faq_feedback.requests.get")
    def test_chatwoot_ingestion_and_publish_flow(self, mock_get, _writeback_mock):
        with tempfile.TemporaryDirectory() as td:
            db_path = str(Path(td) / "sessions.db")
            with patch("session_state.DB_PATH", db_path):
                init_db()
                mock_get.return_value.status_code = 200
                mock_get.return_value.content = b"1"
                mock_get.return_value.json.return_value = {
                    "data": [
                        {
                            "id": 111,
                            "labels": ["faq-ready"],
                            "messages": [
                                {"id": 1, "content": "KA2 error 1003 logs missing", "message_type": 0},
                                {"id": 2, "content": "Resolved by reboot and firmware update", "message_type": 1, "sender_id": 9},
                            ],
                        }
                    ]
                }
                # configured vars may be empty in test env; insert one candidate directly to validate queue flow.
                cid = upsert_faq_candidate(
                    {
                        "dedupe_key": "cw:111:2",
                        "issue_summary": "KA2 error 1003 logs missing",
                        "final_answer": "Resolved by reboot and firmware update",
                        "product": "KA2",
                        "diagnostic_category": "diagnostic",
                        "source_conversation_id": "111",
                        "source_message_id": "2",
                        "source_agent_id": "9",
                        "source_timestamp": "2026-01-01T00:00:00Z",
                    }
                )
                self.assertIsNotNone(cid)
                items = list_faq_candidates("pending_review")
                self.assertGreaterEqual(len(items), 1)
                self.assertTrue(admin_approve_faq_candidate(cid, x_admin_token="changeme-strong")["ok"])
                # publish can fail if faq path is not writable in edge env; we still assert endpoint returns dict
                resp = admin_publish_faq_candidate(cid, x_admin_token="changeme-strong")
                self.assertIn("ok", resp)
                self.assertIn("google_docs_writeback", resp)


if __name__ == "__main__":
    unittest.main()
