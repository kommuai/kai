"""HITL review tickets stored in tenant sessions.db."""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any

from shadou.settings import get_settings


def _db_path() -> str:
    return get_settings().session_db_path


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def init_hitl_tickets_table() -> None:
    conn = sqlite3.connect(_db_path())
    conn.execute("""
        CREATE TABLE IF NOT EXISTS hitl_tickets (
            ticket_id           TEXT PRIMARY KEY,
            created_at          TEXT NOT NULL,
            updated_at          TEXT NOT NULL,
            user_id             TEXT NOT NULL,
            user_question       TEXT NOT NULL,
            bot_answer          TEXT NOT NULL,
            confidence          REAL,
            decision            TEXT,
            fallback_reason     TEXT,
            verification_flagged INTEGER NOT NULL DEFAULT 0,
            impact_reason       TEXT,
            status              TEXT NOT NULL DEFAULT 'open',
            operator_reply      TEXT,
            replied_at          TEXT,
            kb_patch_assistant  TEXT,
            kb_patch_preview    TEXT,
            kb_patch_status     TEXT NOT NULL DEFAULT 'none'
        )
    """)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_hitl_tickets_status ON hitl_tickets(status, created_at DESC)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_hitl_tickets_user ON hitl_tickets(user_id, created_at DESC)"
    )
    conn.commit()
    conn.close()


def _row_to_dict(row: tuple[Any, ...]) -> dict[str, Any]:
    keys = (
        "ticket_id",
        "created_at",
        "updated_at",
        "user_id",
        "user_question",
        "bot_answer",
        "confidence",
        "decision",
        "fallback_reason",
        "verification_flagged",
        "impact_reason",
        "status",
        "operator_reply",
        "replied_at",
        "kb_patch_assistant",
        "kb_patch_preview",
        "kb_patch_status",
    )
    data = dict(zip(keys, row))
    data["verification_flagged"] = bool(data.get("verification_flagged"))
    preview = data.get("kb_patch_preview")
    if isinstance(preview, str) and preview.strip():
        try:
            data["kb_patch_preview"] = json.loads(preview)
        except json.JSONDecodeError:
            pass
    return data


def ticket_exists_for_turn(user_id: str, user_question: str) -> bool:
    init_hitl_tickets_table()
    conn = sqlite3.connect(_db_path())
    row = conn.execute(
        """
        SELECT 1 FROM hitl_tickets
        WHERE user_id = ? AND user_question = ? AND status IN ('open', 'replied')
        LIMIT 1
        """,
        (user_id, user_question),
    ).fetchone()
    conn.close()
    return row is not None


def create_ticket(
    *,
    user_id: str,
    user_question: str,
    bot_answer: str,
    confidence: float,
    decision: str = "",
    fallback_reason: str = "",
    verification_flagged: bool = False,
    impact_reason: str = "",
) -> str:
    init_hitl_tickets_table()
    ticket_id = str(uuid.uuid4())
    now = _now_iso()
    conn = sqlite3.connect(_db_path())
    conn.execute(
        """
        INSERT INTO hitl_tickets (
            ticket_id, created_at, updated_at, user_id, user_question, bot_answer,
            confidence, decision, fallback_reason, verification_flagged, impact_reason,
            status, kb_patch_status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'open', 'none')
        """,
        (
            ticket_id,
            now,
            now,
            user_id,
            user_question,
            bot_answer,
            confidence,
            decision,
            fallback_reason,
            1 if verification_flagged else 0,
            impact_reason,
        ),
    )
    conn.commit()
    conn.close()
    return ticket_id


def list_tickets(*, status: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
    init_hitl_tickets_table()
    conn = sqlite3.connect(_db_path())
    if status:
        rows = conn.execute(
            """
            SELECT ticket_id, created_at, updated_at, user_id, user_question, bot_answer,
                   confidence, decision, fallback_reason, verification_flagged, impact_reason,
                   status, operator_reply, replied_at, kb_patch_assistant, kb_patch_preview, kb_patch_status
            FROM hitl_tickets
            WHERE status = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (status, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT ticket_id, created_at, updated_at, user_id, user_question, bot_answer,
                   confidence, decision, fallback_reason, verification_flagged, impact_reason,
                   status, operator_reply, replied_at, kb_patch_assistant, kb_patch_preview, kb_patch_status
            FROM hitl_tickets
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


def get_ticket(ticket_id: str) -> dict[str, Any] | None:
    init_hitl_tickets_table()
    conn = sqlite3.connect(_db_path())
    row = conn.execute(
        """
        SELECT ticket_id, created_at, updated_at, user_id, user_question, bot_answer,
               confidence, decision, fallback_reason, verification_flagged, impact_reason,
               status, operator_reply, replied_at, kb_patch_assistant, kb_patch_preview, kb_patch_status
        FROM hitl_tickets
        WHERE ticket_id = ?
        LIMIT 1
        """,
        (ticket_id,),
    ).fetchone()
    conn.close()
    return _row_to_dict(row) if row else None


def update_ticket(ticket_id: str, **fields: Any) -> None:
    if not fields:
        return
    init_hitl_tickets_table()
    fields["updated_at"] = _now_iso()
    if "kb_patch_preview" in fields and not isinstance(fields["kb_patch_preview"], str):
        fields["kb_patch_preview"] = json.dumps(fields["kb_patch_preview"])
    cols = ", ".join(f"{k} = ?" for k in fields)
    conn = sqlite3.connect(_db_path())
    conn.execute(f"UPDATE hitl_tickets SET {cols} WHERE ticket_id = ?", (*fields.values(), ticket_id))
    conn.commit()
    conn.close()
