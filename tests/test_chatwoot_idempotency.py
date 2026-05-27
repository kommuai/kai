import os
import sqlite3
import tempfile
import unittest

from kai.integrations.chatwoot import idempotency as idem_mod
from kai.lib.session_state import init_db


class ChatwootIdempotencyTests(unittest.TestCase):
    def setUp(self):
        import kai.lib.session_state as session_state

        self._prev_db_path = session_state.DB_PATH
        self._tmpdir = tempfile.TemporaryDirectory()
        self._db = os.path.join(self._tmpdir.name, "sessions.db")
        os.environ["SESSION_DB_PATH"] = self._db
        from kai.settings import reload_settings

        reload_settings()
        session_state.DB_PATH = self._db
        idem_mod._SCHEMA_READY = False
        init_db()

    def tearDown(self):
        import kai.lib.session_state as session_state

        idem_mod._SCHEMA_READY = False
        session_state.DB_PATH = self._prev_db_path
        os.environ.pop("SESSION_DB_PATH", None)
        from kai.settings import reload_settings

        reload_settings()
        self._tmpdir.cleanup()

    def test_try_mark_processed_once(self):
        self.assertTrue(idem_mod.try_mark_processed("msg-1"))
        self.assertFalse(idem_mod.try_mark_processed("msg-1"))
        self.assertTrue(idem_mod.is_processed("msg-1"))

    def test_schema_created(self):
        idem_mod.try_mark_processed("msg-2")
        import kai.lib.session_state as session_state

        conn = sqlite3.connect(session_state.DB_PATH)
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='chatwoot_processed_messages'"
        ).fetchone()
        conn.close()
        self.assertIsNotNone(row)


if __name__ == "__main__":
    unittest.main()
