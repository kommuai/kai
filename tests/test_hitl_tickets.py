"""HITL ticket creation and high-impact detection."""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from shadou.support_runtime.models import RuntimeResult
from shadou.support_runtime.hitl import maybe_record_hitl_ticket, _impact_reasons
from shadou.workspace.hitl_config import HitlConfig, reload_hitl_config


class ImpactReasonTests(unittest.TestCase):
    def test_keyword_match(self):
        cfg = HitlConfig(impact_keywords=("refund",))
        result = RuntimeResult(decision="direct_answer", answer="x", confidence=0.3)
        reasons = _impact_reasons("I want a refund please", result, cfg)
        self.assertIn("keyword:refund", reasons)

    def test_verification_flagged(self):
        cfg = HitlConfig(flag_verification_fail=True)
        result = RuntimeResult(
            decision="direct_answer",
            answer="x",
            confidence=0.3,
            metadata={"verification": {"flagged": True}},
        )
        reasons = _impact_reasons("hello", result, cfg)
        self.assertIn("verification_failed", reasons)

    def test_no_impact_without_signals(self):
        cfg = HitlConfig(impact_keywords=("refund",))
        result = RuntimeResult(decision="direct_answer", answer="hi", confidence=0.3)
        self.assertEqual(_impact_reasons("hello there", result, cfg), [])


class MaybeRecordHitlTicketTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self._home = Path(self._tmp)
        (self._home / "data").mkdir()
        (self._home / "workspace.yaml").write_text(
            "version: '2'\n"
            "tenant:\n  id: test\n  display_name: Test\n  default_lang: en\n  timezone: UTC\n"
            "session_store:\n  path: data/sessions.db\n"
            "hitl:\n  enabled: true\n  confidence_threshold: 0.6\n"
            "  impact_keywords: [refund]\n"
            "admin:\n  whitelist_numbers: []\n",
            encoding="utf-8",
        )
        os.environ["SHADOU_HOME"] = str(self._home)
        self._clear_caches()

    def tearDown(self):
        os.environ.pop("SHADOU_HOME", None)
        self._clear_caches()

    def _clear_caches(self):
        for fn in (
            "shadou.settings.get_settings",
            "shadou.workspace.manifest.load_workspace_data",
            "shadou.workspace.manifest._load_workspace_manifest_cached",
            "shadou.workspace.hitl_config.get_hitl_config",
            "shadou.workspace.admin_config.get_admin_config",
        ):
            try:
                mod_name, func_name = fn.rsplit(".", 1)
                import importlib
                mod = importlib.import_module(mod_name)
                getattr(mod, func_name).cache_clear()
            except Exception:
                pass
        reload_hitl_config()
        from shadou.workspace.admin_config import reload_admin_config
        reload_admin_config()

    def test_creates_ticket_low_confidence_high_impact(self):
        result = RuntimeResult(decision="direct_answer", answer="Maybe?", confidence=0.4)
        tid = maybe_record_hitl_ticket(user_id="60123456789", user_question="refund my order", result=result)
        self.assertIsNotNone(tid)

        from shadou.lib.hitl_tickets import list_tickets
        tickets = list_tickets(status="open")
        self.assertEqual(len(tickets), 1)
        self.assertEqual(tickets[0]["user_question"], "refund my order")

    def test_skips_high_confidence(self):
        result = RuntimeResult(decision="direct_answer", answer="ok", confidence=0.9)
        tid = maybe_record_hitl_ticket(user_id="60123456789", user_question="refund my order", result=result)
        self.assertIsNone(tid)

    def test_skips_no_impact(self):
        result = RuntimeResult(decision="direct_answer", answer="ok", confidence=0.4)
        tid = maybe_record_hitl_ticket(user_id="60123456789", user_question="hello", result=result)
        self.assertIsNone(tid)

    def test_no_duplicate_ticket(self):
        result = RuntimeResult(decision="direct_answer", answer="?", confidence=0.4)
        q = "refund please"
        t1 = maybe_record_hitl_ticket(user_id="u1", user_question=q, result=result)
        t2 = maybe_record_hitl_ticket(user_id="u1", user_question=q, result=result)
        self.assertIsNotNone(t1)
        self.assertIsNone(t2)


if __name__ == "__main__":
    unittest.main()
