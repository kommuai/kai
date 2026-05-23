from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from kai.lib import session_state

_SCHEMA_READY = False


def _ensure_schema() -> None:
    global _SCHEMA_READY
    if _SCHEMA_READY:
        return
    session_state.init_db()
    conn = sqlite3.connect(session_state.DB_PATH)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chatwoot_processed_messages (
                message_id TEXT PRIMARY KEY,
                processed_at TEXT NOT NULL
            )
            """
        )
        conn.commit()
    finally:
        conn.close()
    _SCHEMA_READY = True


def try_mark_processed(message_id: str) -> bool:
    """Return True if this message id was newly recorded (first time)."""
    mid = str(message_id or "").strip()
    if not mid:
        return False
    _ensure_schema()
    now = datetime.now(timezone.utc).isoformat()
    conn = sqlite3.connect(session_state.DB_PATH)
    try:
        cur = conn.execute(
            "INSERT OR IGNORE INTO chatwoot_processed_messages (message_id, processed_at) VALUES (?, ?)",
            (mid, now),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def is_processed(message_id: str) -> bool:
    mid = str(message_id or "").strip()
    if not mid:
        return False
    _ensure_schema()
    conn = sqlite3.connect(session_state.DB_PATH)
    try:
        row = conn.execute(
            "SELECT 1 FROM chatwoot_processed_messages WHERE message_id = ? LIMIT 1",
            (mid,),
        ).fetchone()
        return row is not None
    finally:
        conn.close()
