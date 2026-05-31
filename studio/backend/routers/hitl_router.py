"""Human-in-the-loop review tickets for low-confidence high-impact chat turns."""
from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from database import get_db
from deps import get_current_user
from hitl_service import apply_kb_patch, propose_kb_patch
from models import Tenant, User
from routers.inbox_router import _deliver_studio_reply_whatsapp, _send_studio_reply
from routers.tenants_router import _assert_tenant_member
from schemas import (
    HitlKbApplyOut,
    HitlKbProposeOut,
    HitlReplyCreate,
    HitlReplyOut,
    HitlTicketListOut,
    HitlTicketOut,
)

router = APIRouter(prefix="/tenants", tags=["hitl"])

OPEN_STATUSES = ("open", "replied")
ARCHIVED_STATUSES = ("resolved", "dismissed", "out_of_scope")


def _is_archived_status(status: str) -> bool:
    return status in ARCHIVED_STATUSES


def _sessions_db_path(tenant: Tenant) -> Path:
    ws = Path(tenant.workspace_home) / "workspace.yaml"
    if not ws.is_file():
        raise HTTPException(status_code=503, detail="workspace.yaml not found for agent")
    data = yaml.safe_load(ws.read_text(encoding="utf-8")) or {}
    rel = (data.get("session_store") or {}).get("path", "data/sessions.db")
    return Path(tenant.workspace_home) / rel


def _hitl_conn(tenant: Tenant) -> sqlite3.Connection:
    path = _sessions_db_path(tenant)
    if not path.is_file():
        raise HTTPException(
            status_code=503,
            detail=f"No sessions database yet at {path}. Run the AI support agent once.",
        )
    os.environ["SHADOU_HOME"] = str(Path(tenant.workspace_home).resolve())
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _init_table(conn: sqlite3.Connection) -> None:
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
    conn.commit()


def _row_to_ticket(row: sqlite3.Row) -> dict[str, Any]:
    import json

    data = dict(row)
    data["verification_flagged"] = bool(data.get("verification_flagged"))
    preview = data.get("kb_patch_preview")
    if isinstance(preview, str) and preview.strip():
        try:
            data["kb_patch_preview"] = json.loads(preview)
        except json.JSONDecodeError:
            data["kb_patch_preview"] = None
    return data


def _get_ticket(conn: sqlite3.Connection, ticket_id: str) -> dict[str, Any]:
    row = conn.execute("SELECT * FROM hitl_tickets WHERE ticket_id = ?", (ticket_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return _row_to_ticket(row)


def _ticket_out(data: dict[str, Any]) -> HitlTicketOut:
    preview = data.get("kb_patch_preview")
    if preview is not None and not isinstance(preview, list):
        preview = None
    return HitlTicketOut(
        ticket_id=data["ticket_id"],
        created_at=data["created_at"],
        updated_at=data["updated_at"],
        user_id=data["user_id"],
        user_question=data["user_question"],
        bot_answer=data["bot_answer"],
        confidence=data.get("confidence"),
        decision=data.get("decision"),
        fallback_reason=data.get("fallback_reason"),
        verification_flagged=bool(data.get("verification_flagged")),
        impact_reason=data.get("impact_reason"),
        status=data["status"],
        operator_reply=data.get("operator_reply"),
        replied_at=data.get("replied_at"),
        kb_patch_status=data.get("kb_patch_status") or "none",
        kb_patch_preview=preview,
    )


@router.get("/{tenant_id}/hitl/tickets", response_model=HitlTicketListOut)
def list_hitl_tickets(
    tenant_id: str,
    queue: str = Query("open", description="open | archived"),
    limit: int = Query(50, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tenant = _assert_tenant_member(tenant_id, user, db)
    conn = _hitl_conn(tenant)
    try:
        _init_table(conn)
        q = (queue or "open").strip().lower()
        if q == "archived":
            placeholders = ",".join("?" for _ in ARCHIVED_STATUSES)
            rows = conn.execute(
                f"""
                SELECT * FROM hitl_tickets
                WHERE status IN ({placeholders})
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (*ARCHIVED_STATUSES, limit),
            ).fetchall()
        else:
            placeholders = ",".join("?" for _ in OPEN_STATUSES)
            rows = conn.execute(
                f"""
                SELECT * FROM hitl_tickets
                WHERE status IN ({placeholders})
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (*OPEN_STATUSES, limit),
            ).fetchall()
        tickets = [_ticket_out(_row_to_ticket(r)) for r in rows]
        return HitlTicketListOut(tickets=tickets, total=len(tickets))
    finally:
        conn.close()


@router.get("/{tenant_id}/hitl/tickets/{ticket_id}", response_model=HitlTicketOut)
def get_hitl_ticket(
    tenant_id: str,
    ticket_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tenant = _assert_tenant_member(tenant_id, user, db)
    conn = _hitl_conn(tenant)
    try:
        _init_table(conn)
        return _ticket_out(_get_ticket(conn, ticket_id))
    finally:
        conn.close()


@router.post("/{tenant_id}/hitl/tickets/{ticket_id}/reply", response_model=HitlReplyOut)
def reply_hitl_ticket(
    tenant_id: str,
    ticket_id: str,
    body: HitlReplyCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tenant = _assert_tenant_member(tenant_id, user, db)
    conn = _hitl_conn(tenant)
    try:
        _init_table(conn)
        ticket = _get_ticket(conn, ticket_id)
        if _is_archived_status(ticket["status"]):
            raise HTTPException(status_code=400, detail="Ticket is archived")

        uid = ticket["user_id"]
        _send_studio_reply(tenant, uid, body.text)
        delivered, detail = _deliver_studio_reply_whatsapp(tenant, uid, body.text)

        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            """
            UPDATE hitl_tickets
            SET operator_reply = ?, replied_at = ?, status = 'replied', updated_at = ?
            WHERE ticket_id = ?
            """,
            (body.text, now, now, ticket_id),
        )
        conn.commit()
        updated = _get_ticket(conn, ticket_id)
        return HitlReplyOut(
            ok=True,
            ticket=_ticket_out(updated),
            channel_delivered=delivered,
            channel_detail=detail,
        )
    finally:
        conn.close()


@router.post("/{tenant_id}/hitl/tickets/{ticket_id}/propose-knowledge", response_model=HitlKbProposeOut)
def propose_hitl_knowledge(
    tenant_id: str,
    ticket_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tenant = _assert_tenant_member(tenant_id, user, db)
    home = Path(tenant.workspace_home).resolve()
    conn = _hitl_conn(tenant)
    try:
        _init_table(conn)
        ticket = _get_ticket(conn, ticket_id)
        if not ticket.get("operator_reply"):
            raise HTTPException(status_code=400, detail="Send a customer reply first")

        import json

        result = propose_kb_patch(home, ticket, tenant_slug=tenant.slug)
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            """
            UPDATE hitl_tickets
            SET kb_patch_assistant = ?, kb_patch_preview = ?, kb_patch_status = 'pending_review', updated_at = ?
            WHERE ticket_id = ?
            """,
            (
                result["assistant_message"],
                json.dumps(result["patches"]),
                now,
                ticket_id,
            ),
        )
        conn.commit()
        updated = _get_ticket(conn, ticket_id)
        return HitlKbProposeOut(
            ok=True,
            ticket=_ticket_out(updated),
            patches=result["patches"],
            summary=result.get("summary") or "",
        )
    finally:
        conn.close()


@router.post("/{tenant_id}/hitl/tickets/{ticket_id}/apply-knowledge", response_model=HitlKbApplyOut)
def apply_hitl_knowledge(
    tenant_id: str,
    ticket_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tenant = _assert_tenant_member(tenant_id, user, db)
    home = Path(tenant.workspace_home).resolve()
    conn = _hitl_conn(tenant)
    try:
        _init_table(conn)
        ticket = _get_ticket(conn, ticket_id)
        assistant = (ticket.get("kb_patch_assistant") or "").strip()
        if not assistant:
            raise HTTPException(status_code=400, detail="No pending KB patch — propose one first")
        if ticket.get("kb_patch_status") != "pending_review":
            raise HTTPException(status_code=400, detail="KB patch is not pending review")

        applied_payload = apply_kb_patch(home, assistant)
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            """
            UPDATE hitl_tickets
            SET kb_patch_status = 'applied', status = 'resolved', updated_at = ?
            WHERE ticket_id = ?
            """,
            (now, ticket_id),
        )
        conn.commit()
        updated = _get_ticket(conn, ticket_id)
        return HitlKbApplyOut(
            ok=True,
            ticket=_ticket_out(updated),
            applied=applied_payload.get("applied") or [],
            summary=applied_payload.get("summary") or "",
            compile=applied_payload.get("compile"),
        )
    finally:
        conn.close()


@router.post("/{tenant_id}/hitl/tickets/{ticket_id}/reject-knowledge", response_model=HitlTicketOut)
def reject_hitl_knowledge(
    tenant_id: str,
    ticket_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tenant = _assert_tenant_member(tenant_id, user, db)
    conn = _hitl_conn(tenant)
    try:
        _init_table(conn)
        _get_ticket(conn, ticket_id)
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            """
            UPDATE hitl_tickets
            SET kb_patch_status = 'rejected', updated_at = ?
            WHERE ticket_id = ?
            """,
            (now, ticket_id),
        )
        conn.commit()
        return _ticket_out(_get_ticket(conn, ticket_id))
    finally:
        conn.close()


@router.post("/{tenant_id}/hitl/tickets/{ticket_id}/out-of-scope", response_model=HitlTicketOut)
def out_of_scope_hitl_ticket(
    tenant_id: str,
    ticket_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark ticket out of scope — no customer message, archive immediately."""
    tenant = _assert_tenant_member(tenant_id, user, db)
    conn = _hitl_conn(tenant)
    try:
        _init_table(conn)
        ticket = _get_ticket(conn, ticket_id)
        if _is_archived_status(ticket["status"]):
            raise HTTPException(status_code=400, detail="Ticket is already archived")
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "UPDATE hitl_tickets SET status = 'out_of_scope', updated_at = ? WHERE ticket_id = ?",
            (now, ticket_id),
        )
        conn.commit()
        return _ticket_out(_get_ticket(conn, ticket_id))
    finally:
        conn.close()


@router.post("/{tenant_id}/hitl/tickets/{ticket_id}/dismiss", response_model=HitlTicketOut)
def dismiss_hitl_ticket(
    tenant_id: str,
    ticket_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tenant = _assert_tenant_member(tenant_id, user, db)
    conn = _hitl_conn(tenant)
    try:
        _init_table(conn)
        _get_ticket(conn, ticket_id)
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "UPDATE hitl_tickets SET status = 'dismissed', updated_at = ? WHERE ticket_id = ?",
            (now, ticket_id),
        )
        conn.commit()
        return _ticket_out(_get_ticket(conn, ticket_id))
    finally:
        conn.close()
