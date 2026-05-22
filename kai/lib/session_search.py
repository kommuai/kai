"""FTS5 search over per-user message index (Hermes session_search-inspired, scoped to one user)."""

from __future__ import annotations

import re
import sqlite3
from datetime import datetime, timezone

from kai.lib.session_state import DB_PATH, init_db

_MAX_SNIPPET = 280


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_message_index_schema() -> None:
    """Create message index + FTS (idempotent). Called from init_db()."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS session_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            role TEXT NOT NULL,
            text TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    c.execute(
        "CREATE INDEX IF NOT EXISTS idx_session_messages_user ON session_messages(user_id, id DESC)"
    )
    c.execute(
        """
        CREATE VIRTUAL TABLE IF NOT EXISTS session_messages_fts
        USING fts5(text, user_id UNINDEXED)
        """
    )
    conn.commit()
    conn.close()


def index_message(user_id: str, role: str, text: str) -> None:
    """Append one searchable row for this user (same user_id scope as WhatsApp phone)."""
    msg = (text or "").strip()
    if not user_id or not msg:
        return
    ensure_message_index_schema()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    created = _now_iso()
    c.execute(
        "INSERT INTO session_messages (user_id, role, text, created_at) VALUES (?, ?, ?, ?)",
        (user_id, role, msg[:8000], created),
    )
    row_id = c.lastrowid
    c.execute(
        "INSERT INTO session_messages_fts (rowid, text, user_id) VALUES (?, ?, ?)",
        (row_id, msg[:8000], user_id),
    )
    conn.commit()
    conn.close()


def _sanitize_fts_query(query: str) -> str:
    """Strip FTS operators; keep alphanumeric tokens."""
    tokens = re.findall(r"[a-zA-Z0-9]{2,}", (query or "").lower())
    if not tokens:
        return ""
    return " ".join(tokens[:12])


def search_user_messages(
    user_id: str,
    query: str,
    *,
    limit: int = 5,
) -> dict:
    """Search prior turns for this user only (privacy: no cross-user search)."""
    if not user_id:
        return {"ok": False, "error": "missing_user_id", "results": []}
    q = _sanitize_fts_query(query)
    if not q:
        return {"ok": False, "error": "empty_query", "results": []}

    ensure_message_index_schema()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute(
            """
            SELECT m.id, m.role, m.text, m.created_at
            FROM session_messages_fts f
            JOIN session_messages m ON m.id = f.rowid
            WHERE session_messages_fts MATCH ?
              AND m.user_id = ?
            ORDER BY m.id DESC
            LIMIT ?
            """,
            (q, user_id, max(1, min(limit, 20))),
        )
        rows = c.fetchall()
    except sqlite3.OperationalError as exc:
        conn.close()
        return {"ok": False, "error": f"fts_error:{exc}", "results": []}
    conn.close()

    results = []
    for mid, role, text, created_at in rows:
        body = (text or "").strip()
        if len(body) > _MAX_SNIPPET:
            body = body[:_MAX_SNIPPET] + "…"
        results.append({
            "message_id": mid,
            "role": role,
            "snippet": body,
            "created_at": created_at,
        })
    return {"ok": True, "query": q, "user_scope": user_id, "results": results}
