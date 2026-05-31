"""Low-confidence event log for the admin learning flow."""

from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any

from shadou.settings import get_settings


def _db_path() -> str:
    return get_settings().session_db_path


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def init_learning_events_table() -> None:
    conn = sqlite3.connect(_db_path())
    conn.execute("""
        CREATE TABLE IF NOT EXISTS learning_events (
            event_id    TEXT PRIMARY KEY,
            created_at  TEXT NOT NULL,
            user_id     TEXT NOT NULL,
            user_text   TEXT NOT NULL,
            decision    TEXT,
            confidence  REAL,
            fallback_reason TEXT,
            trace_id    TEXT,
            status      TEXT NOT NULL DEFAULT 'new'
        )
    """)
    conn.commit()
    conn.close()


def record_event(
    *,
    user_id: str,
    user_text: str,
    decision: str = "",
    confidence: float = 0.0,
    fallback_reason: str = "",
    trace_id: str = "",
) -> str:
    event_id = str(uuid.uuid4())
    conn = sqlite3.connect(_db_path())
    conn.execute(
        """
        INSERT INTO learning_events
            (event_id, created_at, user_id, user_text, decision, confidence, fallback_reason, trace_id, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'new')
        """,
        (event_id, _now_iso(), user_id, user_text, decision, confidence, fallback_reason, trace_id),
    )
    conn.commit()
    conn.close()
    return event_id


def fetch_pending_events(limit: int = 10) -> list[dict[str, Any]]:
    init_learning_events_table()
    conn = sqlite3.connect(_db_path())
    rows = conn.execute(
        """
        SELECT event_id, created_at, user_id, user_text, decision, confidence, fallback_reason, trace_id, status
        FROM learning_events
        WHERE status = 'new'
        ORDER BY created_at ASC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    conn.close()
    keys = ("event_id", "created_at", "user_id", "user_text", "decision", "confidence", "fallback_reason", "trace_id", "status")
    return [dict(zip(keys, row)) for row in rows]


def set_event_status(event_id: str, status: str) -> None:
    conn = sqlite3.connect(_db_path())
    conn.execute("UPDATE learning_events SET status = ? WHERE event_id = ?", (status, event_id))
    conn.commit()
    conn.close()
