import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from kai.lib.session_state import append_human_segment_turn, get_session, init_db, reset_memory, start_human_segment
from kai.support_runtime.background_review import schedule_faq_learn_after_handback
from kai.support_runtime.faq_learn import is_plausible_unified_diff, run_faq_learn

_SAMPLE_DIFF = """--- a/master_faq.md
+++ b/master_faq.md
@@ -10,1 +10,2 @@
 old line
+new line
"""

_SAMPLE_JSON = """```json
{"summary": "test", "intent_updates": [{"intent_id": "test", "answer_append": "more"}]}
```
"""


class FaqLearnTests(unittest.TestCase):
    def test_is_plausible_unified_diff(self):
        self.assertTrue(is_plausible_unified_diff(_SAMPLE_DIFF))
        self.assertFalse(is_plausible_unified_diff("just prose"))
        self.assertTrue(is_plausible_unified_diff("```diff\n" + _SAMPLE_DIFF + "\n```"))

    def test_run_faq_learn_writes_queue(self):
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            db_path = str(td_path / "sessions.db")
            qroot = td_path / "learn_queue"
            master = td_path / "master_faq.md"
            master.write_text("## intent: test\naliases:\n- hi\nanswer:\nhello\n", encoding="utf-8")
            with patch("kai.lib.session_state.DB_PATH", db_path):
                init_db()
            raw = _SAMPLE_JSON + "\n" + _SAMPLE_DIFF
            with patch("kai.support_runtime.faq_learn_queue.FAQ_LEARN_QUEUE_DIR", str(qroot)):
                with patch("kai.support_runtime.faq_learn.resolve_master_faq_path", return_value=str(master)):
                    with patch("kai.support_runtime.faq_learn.KAI_LLM_API_KEY", "fake"):
                        with patch("kai.support_runtime.faq_learn.KAI_FAQ_LEARN_ENABLED", "1"):
                            with patch("kai.support_runtime.faq_learn.KAI_FAQ_LEARN_USE_QUEUE", "1"):
                                prov = Mock()

                                class _P:
                                    def chat(self, *a, **k):
                                        return raw

                                prov.return_value = _P()
                                with patch("kai.support_runtime.faq_learn.build_provider", prov):
                                    out = run_faq_learn(
                                        "u1",
                                        [{"role": "user", "text": "need refund policy"}],
                                        "",
                                    )
            self.assertTrue(out.get("ok"))
            pid = out.get("proposal_id")
            self.assertTrue((qroot / pid / "proposal.diff").exists())

    def test_run_faq_learn_legacy_append(self):
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            learnt = td_path / "agent_learnt_faq.md"
            master = td_path / "master_faq.md"
            master.write_text("## intent: test\naliases:\n- hi\nanswer:\nhello\n", encoding="utf-8")
            raw = _SAMPLE_DIFF
            with patch("kai.support_runtime.faq_learn.resolve_master_faq_path", return_value=str(master)):
                with patch("kai.support_runtime.faq_learn.AGENT_LEARNT_FAQ_PATH", str(learnt)):
                    with patch("kai.support_runtime.faq_learn.KAI_FAQ_LEARN_USE_QUEUE", "0"):
                        with patch("kai.support_runtime.faq_learn.KAI_FAQ_LEARN_LEGACY_APPEND", "1"):
                            with patch("kai.support_runtime.faq_learn.KAI_LLM_API_KEY", "fake"):
                                with patch("kai.support_runtime.faq_learn.KAI_FAQ_LEARN_ENABLED", "1"):
                                    prov = Mock()

                                    class _P:
                                        def chat(self, *a, **k):
                                            return raw

                                    prov.return_value = _P()
                                    with patch("kai.support_runtime.faq_learn.build_provider", prov):
                                        out = run_faq_learn("u1", [{"role": "user", "text": "x"}], "")
            self.assertTrue(out.get("ok"))
            text = learnt.read_text(encoding="utf-8")
            self.assertIn("--- a/master_faq.md", text)

    def test_schedule_pops_segment(self):
        with tempfile.TemporaryDirectory() as td:
            db_path = str(Path(td) / "sessions.db")
            with patch("kai.lib.session_state.DB_PATH", db_path):
                init_db()
                uid = "seg_user"
                reset_memory(uid)
                start_human_segment(uid, None)
                append_human_segment_turn(uid, "user", "help")
                with patch("kai.support_runtime.background_review.run_faq_learn", return_value={"ok": True}) as m:
                    with patch("kai.support_runtime.background_review.KAI_FAQ_LEARN_ASYNC", "0"):
                        schedule_faq_learn_after_handback(uid)
                m.assert_called_once()
                sess = get_session(uid)
                self.assertFalse(sess.get("human_segment_open"))


if __name__ == "__main__":
    unittest.main()
