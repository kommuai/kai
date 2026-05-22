import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from kai.core.faq_markdown import parse_master_faq_schema
from kai.support_runtime.faq_learn import _extract_json_proposal, run_faq_learn
from kai.support_runtime.faq_learn_queue import (
    list_proposals,
    load_proposal,
    make_proposal_id,
    set_proposal_status,
    write_proposal,
)
from kai.support_runtime.faq_merge import apply_proposal_json_to_master

_SAMPLE_DIFF = """--- a/master_faq.md
+++ b/master_faq.md
@@ -1,1 +1,2 @@
 line
+added
"""

_SAMPLE_JSON = {
    "summary": "Corolla install steps",
    "intent_updates": [
        {
            "intent_id": "vehicle_corolla_cross",
            "aliases_add": ["corolla cross install"],
            "answer_append": "Use the 2021+ harness guide.",
        }
    ],
    "pitfalls": ["Do not ask year when vehicle already named"],
}


class LearnQueueTests(unittest.TestCase):
    def test_extract_json_proposal(self):
        raw = "```json\n" + json.dumps(_SAMPLE_JSON) + "\n```\n" + _SAMPLE_DIFF
        got = _extract_json_proposal(raw)
        self.assertEqual(got.get("summary"), _SAMPLE_JSON["summary"])

    def test_write_and_list_proposal(self):
        with tempfile.TemporaryDirectory() as td:
            qroot = Path(td) / "learn_queue"
            with patch("kai.support_runtime.faq_learn_queue.FAQ_LEARN_QUEUE_DIR", str(qroot)):
                pid = make_proposal_id("u1", "resume")
                write_proposal(
                    pid,
                    meta={"status": "pending", "trigger": "resume"},
                    transcript="user: hi",
                    diff_text=_SAMPLE_DIFF,
                    proposal=_SAMPLE_JSON,
                )
                pending = list_proposals(status="pending")
                self.assertEqual(len(pending), 1)
                loaded = load_proposal(pid)
                self.assertEqual(loaded["proposal"]["summary"], _SAMPLE_JSON["summary"])
                set_proposal_status(pid, "merged")
                self.assertEqual(len(list_proposals(status="pending")), 0)

    def test_merge_proposal_json(self):
        with tempfile.TemporaryDirectory() as td:
            master = Path(td) / "master_faq.md"
            master.write_text(
                "## intent: vehicle_corolla_cross\naliases:\n- corolla\nanswer:\nOld.\n",
                encoding="utf-8",
            )
            out = apply_proposal_json_to_master(_SAMPLE_JSON, master)
            self.assertTrue(out.get("ok"))
            schema = parse_master_faq_schema(master.read_text(encoding="utf-8"))
            row = next(r for r in schema["intents"] if r["intent_id"] == "vehicle_corolla_cross")
            self.assertIn("corolla cross install", row["aliases"])
            self.assertIn("harness guide", row["answer"])

    def test_run_faq_learn_writes_queue(self):
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            qroot = td_path / "learn_queue"
            master = td_path / "master_faq.md"
            master.write_text("## intent: test\naliases:\n- hi\nanswer:\nhello\n", encoding="utf-8")
            raw = "```json\n" + json.dumps(_SAMPLE_JSON) + "\n```\n" + _SAMPLE_DIFF
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
                                        [{"role": "user", "text": "Corolla install"}],
                                        "",
                                        trigger="resume",
                                    )
            self.assertTrue(out.get("ok"))
            self.assertTrue((qroot / out["proposal_id"] / "proposal.json").exists())


if __name__ == "__main__":
    unittest.main()
