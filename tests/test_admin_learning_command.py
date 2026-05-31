"""Tests for admin mode-switching (/admin, /test) and /learning command flow."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch
from uuid import uuid4

from shadou.lib.learning_events import (
    fetch_pending_events,
    init_learning_events_table,
    record_event,
    set_event_status,
)
from shadou.lib.session_state import freeze, get_session, init_db, reset_memory
from shadou.services.shadou_service import ShadouService


def _svc() -> ShadouService:
    return ShadouService()


def _uid(prefix: str = "admin") -> str:
    return f"+60{prefix}{uuid4().hex[:6]}"


ADMIN_NUMBER = "+60199999999"
NON_ADMIN_NUMBER = "+60188888888"


def _patch_whitelist(whitelist: list[str]):
    """Patch get_admin_config to return a whitelist containing the given numbers."""
    from shadou.workspace.admin_config import AdminConfig, AdminLearningConfig

    cfg = AdminConfig(
        whitelist_numbers=frozenset(whitelist),
        learning=AdminLearningConfig(enabled=True, min_confidence=0.6, max_items=10),
    )
    return patch("shadou.workspace.admin_config.get_admin_config", return_value=cfg)


class AdminModeCommandTests(unittest.TestCase):
    def setUp(self):
        init_db()
        init_learning_events_table()
        reset_memory(ADMIN_NUMBER)
        reset_memory(NON_ADMIN_NUMBER)

    def _msg(self, phone: str, text: str) -> dict:
        return {"phone_number": phone, "content": text}

    # ------------------------------------------------------------------ /admin
    def test_admin_from_non_whitelisted_returns_none(self):
        svc = _svc()
        with _patch_whitelist([ADMIN_NUMBER]):
            result = svc.pre_router(self._msg(NON_ADMIN_NUMBER, "/admin"))
        # non-admin: pre_router should NOT intercept
        self.assertIsNone(result)

    def test_admin_from_whitelisted_freezes_session(self):
        svc = _svc()
        with _patch_whitelist([ADMIN_NUMBER]):
            result = svc.pre_router(self._msg(ADMIN_NUMBER, "/admin"))
        self.assertIsNotNone(result)
        self.assertEqual(result["type"], "reply")
        sess = get_session(ADMIN_NUMBER)
        self.assertTrue(sess.get("frozen"))
        self.assertTrue(sess.get("admin_mode"))

    def test_admin_sets_admin_mode_true(self):
        svc = _svc()
        with _patch_whitelist([ADMIN_NUMBER]):
            svc.pre_router(self._msg(ADMIN_NUMBER, "/admin"))
        sess = get_session(ADMIN_NUMBER)
        self.assertTrue(sess.get("admin_mode"))

    # ------------------------------------------------------------------ /test
    def test_test_unfreezes_session(self):
        svc = _svc()
        freeze(ADMIN_NUMBER, True)
        sess = get_session(ADMIN_NUMBER)
        sess["admin_mode"] = True
        from shadou.lib.session_state import save_session
        save_session(ADMIN_NUMBER, sess)

        with _patch_whitelist([ADMIN_NUMBER]):
            result = svc.pre_router(self._msg(ADMIN_NUMBER, "/test"))
        self.assertIsNotNone(result)
        sess = get_session(ADMIN_NUMBER)
        self.assertFalse(sess.get("frozen"))
        self.assertFalse(sess.get("admin_mode"))

    def test_test_clears_learning_state(self):
        svc = _svc()
        from shadou.lib.session_state import save_session
        sess = get_session(ADMIN_NUMBER)
        sess["admin_mode"] = True
        sess["learning_state"] = {"event_ids": ["x"], "index": 0, "current_event_id": "x"}
        save_session(ADMIN_NUMBER, sess)

        with _patch_whitelist([ADMIN_NUMBER]):
            svc.pre_router(self._msg(ADMIN_NUMBER, "/test"))
        sess = get_session(ADMIN_NUMBER)
        self.assertIsNone(sess.get("learning_state"))

    # ------------------------------------------------------------------ /learning gating
    def test_learning_while_not_admin_mode_returns_nudge(self):
        svc = _svc()
        with _patch_whitelist([ADMIN_NUMBER]):
            result = svc.pre_router(self._msg(ADMIN_NUMBER, "/learning"))
        self.assertIsNotNone(result)
        self.assertIn("admin", result["message"].lower())

    def test_learning_while_admin_mode_no_events(self):
        svc = _svc()
        from shadou.lib.session_state import save_session
        sess = get_session(ADMIN_NUMBER)
        sess["admin_mode"] = True
        save_session(ADMIN_NUMBER, sess)

        with _patch_whitelist([ADMIN_NUMBER]):
            with patch("shadou.lib.learning_events.fetch_pending_events", return_value=[]):
                result = svc.pre_router(self._msg(ADMIN_NUMBER, "/learning"))
        self.assertIsNotNone(result)
        self.assertIn("No new", result["message"])

    def test_learning_with_events_presents_first_question(self):
        svc = _svc()
        from shadou.lib.session_state import save_session
        sess = get_session(ADMIN_NUMBER)
        sess["admin_mode"] = True
        save_session(ADMIN_NUMBER, sess)

        fake_event = {
            "event_id": "ev1",
            "user_text": "How do I install the device?",
            "user_id": NON_ADMIN_NUMBER,
            "confidence": 0.4,
            "decision": "fallback",
            "fallback_reason": "",
            "trace_id": "t1",
            "created_at": "2026-01-01",
            "status": "new",
        }
        with _patch_whitelist([ADMIN_NUMBER]):
            with patch("shadou.lib.learning_events.fetch_pending_events", return_value=[fake_event]):
                result = svc.pre_router(self._msg(ADMIN_NUMBER, "/learning"))

        self.assertIsNotNone(result)
        self.assertIn("How do I install", result["message"])
        sess = get_session(ADMIN_NUMBER)
        self.assertIsNotNone(sess.get("learning_state"))
        self.assertEqual(sess["learning_state"]["current_event_id"], "ev1")

    def test_learning_skip_advances_to_next(self):
        svc = _svc()
        from shadou.lib.session_state import save_session
        uid = ADMIN_NUMBER
        sess = get_session(uid)
        sess["admin_mode"] = True
        sess["learning_state"] = {
            "event_ids": ["ev1", "ev2"],
            "index": 0,
            "current_event_id": "ev1",
        }
        save_session(uid, sess)

        fake_ev2 = {
            "event_id": "ev2",
            "user_text": "What warranty do I get?",
            "user_id": NON_ADMIN_NUMBER,
            "confidence": 0.3,
            "decision": "fallback",
            "fallback_reason": "",
            "trace_id": "t2",
            "created_at": "2026-01-01",
            "status": "new",
        }
        with _patch_whitelist([ADMIN_NUMBER]):
            with patch("shadou.lib.learning_events.set_event_status"):
                with patch("shadou.lib.learning_events.fetch_pending_events", return_value=[fake_ev2]):
                    result = svc.pre_router(self._msg(uid, "/learning skip"))

        self.assertIsNotNone(result)
        self.assertIn("What warranty", result["message"])

    def test_learning_stop_clears_state(self):
        svc = _svc()
        from shadou.lib.session_state import save_session
        uid = ADMIN_NUMBER
        sess = get_session(uid)
        sess["admin_mode"] = True
        sess["learning_state"] = {
            "event_ids": ["ev1"],
            "index": 0,
            "current_event_id": "ev1",
        }
        save_session(uid, sess)

        with _patch_whitelist([ADMIN_NUMBER]):
            result = svc.pre_router(self._msg(uid, "/learning stop"))

        self.assertIsNotNone(result)
        sess = get_session(uid)
        self.assertIsNone(sess.get("learning_state"))

    # ------------------------------------------------------------------ low-confidence event capture
    def test_low_confidence_result_inserts_event_for_non_admin(self):
        uid = f"+601{uuid4().hex[:6]}"
        event_id = record_event(
            user_id=uid,
            user_text="what is the price?",
            decision="fallback",
            confidence=0.4,
            trace_id="t99",
        )
        events = fetch_pending_events(limit=50)
        ids = [e["event_id"] for e in events]
        self.assertIn(event_id, ids)

    def test_set_event_status_resolved(self):
        uid = f"+601{uuid4().hex[:6]}"
        event_id = record_event(
            user_id=uid,
            user_text="how to connect?",
            confidence=0.3,
        )
        set_event_status(event_id, "resolved")
        events = fetch_pending_events(limit=50)
        ids = [e["event_id"] for e in events]
        self.assertNotIn(event_id, ids)


if __name__ == "__main__":
    unittest.main()
