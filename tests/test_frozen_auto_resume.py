"""Auto-resume bot after live-agent freeze exceeds SESSION_IDLE_HOURS."""

from __future__ import annotations

import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from shadou.lib.session_state import (
    auto_unfreeze_stale_handoff,
    ensure_active_session,
    freeze,
    get_session,
    init_db,
    reset_memory,
    save_session,
)
from shadou.services.container import shadou_service


class FrozenAutoResumeTests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        os.environ["SESSION_DB_PATH"] = os.path.join(self._tmpdir, "sessions.db")
        init_db()
        self.uid = f"frozen_{uuid4().hex[:8]}"
        reset_memory(self.uid)

    def test_auto_unfreeze_after_frozen_at_threshold(self):
        freeze(self.uid, True)
        old = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
        sess = get_session(self.uid)
        sess["frozen_at"] = old
        save_session(self.uid, sess)
        self.assertTrue(auto_unfreeze_stale_handoff(self.uid))
        self.assertFalse(get_session(self.uid).get("frozen"))

    def test_stays_frozen_within_threshold(self):
        freeze(self.uid, True)
        self.assertFalse(auto_unfreeze_stale_handoff(self.uid))
        self.assertTrue(get_session(self.uid).get("frozen"))

    def test_idle_session_reset_clears_frozen(self):
        freeze(self.uid, True)
        old = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
        sess = get_session(self.uid)
        sess["last_activity_at"] = old
        sess["session_started_at"] = old
        save_session(self.uid, sess)
        ensure_active_session(self.uid)
        self.assertFalse(get_session(self.uid).get("frozen"))

    def test_manual_resume_sends_ack(self):
        freeze(self.uid, True)
        out = shadou_service.pre_router({"content": "resume", "phone_number": self.uid})
        self.assertEqual(out.get("type"), "reply")
        self.assertIn("Bot resumed", out.get("message", ""))
        self.assertEqual(out.get("next_state"), "bot")
        self.assertFalse(get_session(self.uid).get("frozen"))

    def test_auto_unfreeze_does_not_send_resume_ack(self):
        freeze(self.uid, True)
        old = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
        sess = get_session(self.uid)
        sess["frozen_at"] = old
        save_session(self.uid, sess)
        out = shadou_service.pre_router({"content": "what is the price?", "phone_number": self.uid})
        self.assertIsNone(out)
        self.assertFalse(get_session(self.uid).get("frozen"))

    def test_pre_router_processes_message_after_stale_handoff(self):
        freeze(self.uid, True)
        old = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
        sess = get_session(self.uid)
        sess["frozen_at"] = old
        save_session(self.uid, sess)
        out = shadou_service.pre_router({"content": "what is the price?", "phone_number": self.uid})
        self.assertIsNone(out)
        self.assertFalse(get_session(self.uid).get("frozen"))


if __name__ == "__main__":
    unittest.main()
