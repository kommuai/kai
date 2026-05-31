"""Session idle window (default 24h) resets chat history."""

from __future__ import annotations

import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from shadou.lib.session_state import (
    add_message_to_history,
    ensure_active_session,
    get_history,
    get_session,
    init_db,
    reset_memory,
    save_session,
)


class SessionIdleTests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        os.environ["SESSION_DB_PATH"] = os.path.join(self._tmpdir, "sessions.db")
        init_db()
        self.uid = f"idle_{uuid4().hex[:8]}"
        reset_memory(self.uid)

    def test_idle_session_clears_history(self):
        add_message_to_history(self.uid, "user", "hello")
        self.assertEqual(len(get_history(self.uid)), 1)
        old = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
        sess = get_session(self.uid)
        sess["last_activity_at"] = old
        sess["session_started_at"] = old
        save_session(self.uid, sess)
        reset = ensure_active_session(self.uid)
        self.assertTrue(reset)
        self.assertEqual(get_history(self.uid), [])


if __name__ == "__main__":
    unittest.main()
