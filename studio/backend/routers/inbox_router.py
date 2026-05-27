"""Read-only inbox + contacts backed by tenant sessions.db; contact tags in admin.db."""
from __future__ import annotations

import json
import os
import re
import sqlite3
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_
from sqlalchemy.orm import Session

from database import get_db
from deps import get_current_user
from models import ContactTag, Tenant, User
from routers.tenants_router import KAI_REPO, _assert_tenant_member
from schemas import (
    ChatwootAccountLabelsOut,
    ChatwootLabelsBody,
    ChatwootMetaOut,
    ChatwootPrivateNoteBody,
    ChatwootStatusBody,
    ContactDetailOut,
    ContactListOut,
    ContactOut,
    ConversationDetailOut,
    ConversationListOut,
    ConversationOut,
    MemoryFactOut,
    MessageOut,
    ReplyCreate,
    ReplyOut,
    SearchResultsOut,
    SearchHitOut,
    TagCreate,
)

router = APIRouter(prefix="/tenants", tags=["inbox"])


def _sessions_db_path(tenant: Tenant) -> Path:
    ws = Path(tenant.workspace_home) / "workspace.yaml"
    if not ws.is_file():
        raise HTTPException(status_code=503, detail="workspace.yaml not found for tenant")
    data = yaml.safe_load(ws.read_text(encoding="utf-8")) or {}
    rel = (data.get("session_store") or {}).get("path", "data/sessions.db")
    return Path(tenant.workspace_home) / rel


def _open_sessions_ro(tenant: Tenant) -> tuple[sqlite3.Connection | None, Path]:
    path = _sessions_db_path(tenant)
    if not path.is_file():
        return None, path
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn, path


def _sanitize_fts_query(query: str) -> str:
    tokens = re.findall(r"[a-zA-Z0-9]{2,}", (query or "").lower())
    if not tokens:
        return ""
    return " ".join(tokens[:12])


def _parse_session_data(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except Exception:
        return {}


def _history_preview(history: list[Any], max_len: int = 140) -> str:
    if not history:
        return ""
    last = history[-1]
    if isinstance(last, dict):
        text = str(last.get("text", "") or "")
    else:
        text = str(last)
    text = text.strip().replace("\n", " ")
    if len(text) > max_len:
        return text[: max_len - 1] + "…"
    return text


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    cur = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type IN ('table','virtual') AND name=? LIMIT 1",
        (name,),
    )
    return cur.fetchone() is not None


def _display_name_from_facts(facts: list[MemoryFactOut]) -> str:
    for f in facts:
        if f.fact_type == "identity" and f.fact_key.lower() in ("name", "display_name", "full_name"):
            if f.fact_value.strip():
                return f.fact_value.strip()
    for f in facts:
        if f.fact_value.strip():
            return f.fact_value.strip()[:80]
    return ""


@router.get("/{tenant_id}/inbox/conversations", response_model=ConversationListOut)
def list_conversations(
    tenant_id: str,
    conv_status: str = Query("all", alias="status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tenant = _assert_tenant_member(tenant_id, user, db)
    if conv_status not in ("all", "active", "frozen"):
        raise HTTPException(status_code=400, detail="status must be all, active, or frozen")
    ro, path = _open_sessions_ro(tenant)
    if ro is None:
        raise HTTPException(
            status_code=503,
            detail=f"No sessions database yet at {path}. Run the bot once to create sessions.",
        )
    try:
        cur = ro.execute("SELECT user_id, data FROM sessions")
        rows = cur.fetchall()
    finally:
        ro.close()

    items: list[dict[str, Any]] = []
    for row in rows:
        uid = row["user_id"]
        data = _parse_session_data(row["data"])
        frozen = bool(data.get("frozen"))
        if conv_status == "active" and frozen:
            continue
        if conv_status == "frozen" and not frozen:
            continue
        history = data.get("history") or []
        if not isinstance(history, list):
            history = []
        last_at = data.get("last_activity_at")
        items.append(
            {
                "user_id": uid,
                "frozen": frozen,
                "last_activity_at": last_at if isinstance(last_at, str) else None,
                "last_message_preview": _history_preview(history),
                "message_count": len(history),
                "_sort": last_at or "",
            }
        )

    items.sort(key=lambda x: x["_sort"], reverse=True)
    for it in items:
        it.pop("_sort", None)
    total = len(items)
    slice_items = items[offset : offset + max(1, min(limit, 200))]
    return ConversationListOut(
        items=[
            ConversationOut(
                user_id=x["user_id"],
                frozen=x["frozen"],
                last_activity_at=x["last_activity_at"],
                last_message_preview=x["last_message_preview"],
                message_count=x["message_count"],
            )
            for x in slice_items
        ],
        total=total,
    )


@router.get("/{tenant_id}/inbox/conversations/search", response_model=SearchResultsOut)
def search_messages_global(
    tenant_id: str,
    q: str,
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tenant = _assert_tenant_member(tenant_id, user, db)
    fts_q = _sanitize_fts_query(q)
    if not fts_q:
        raise HTTPException(status_code=400, detail="Search query too short or invalid")

    ro, path = _open_sessions_ro(tenant)
    if ro is None:
        raise HTTPException(status_code=503, detail=f"No sessions database at {path}")
    hits: list[SearchHitOut] = []
    try:
        if not _table_exists(ro, "session_messages_fts"):
            return SearchResultsOut(query=fts_q, items=[])
        cur = ro.execute(
            """
            SELECT m.id, m.user_id, m.role, m.text, m.created_at
            FROM session_messages_fts f
            JOIN session_messages m ON m.id = f.rowid
            WHERE f MATCH ?
            ORDER BY m.id DESC
            LIMIT ? OFFSET ?
            """,
            (fts_q, max(1, min(limit, 100)), max(0, offset)),
        )
        for mid, uid, role, text, created in cur.fetchall():
            body = (text or "").strip().replace("\n", " ")
            if len(body) > 280:
                body = body[:279] + "…"
            hits.append(
                SearchHitOut(
                    user_id=str(uid),
                    message_id=int(mid),
                    role=str(role),
                    snippet=body,
                    created_at=str(created),
                )
            )
    except sqlite3.OperationalError:
        hits = []
    finally:
        ro.close()
    return SearchResultsOut(query=fts_q, items=hits)


@router.get("/{tenant_id}/inbox/conversations/{user_id:path}", response_model=ConversationDetailOut)
def get_conversation(
    tenant_id: str,
    user_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tenant = _assert_tenant_member(tenant_id, user, db)
    ro, path = _open_sessions_ro(tenant)
    if ro is None:
        raise HTTPException(status_code=503, detail=f"No sessions database at {path}")
    tags = [r.tag for r in db.query(ContactTag).filter(ContactTag.tenant_id == tenant_id, ContactTag.user_id == user_id).all()]
    tags = sorted(set(tags))
    facts: list[MemoryFactOut] = []
    messages: list[MessageOut] = []
    frozen = False
    last_activity_at: str | None = None
    chatwoot_conversation_id: str | None = None
    try:
        cur = ro.execute("SELECT data FROM sessions WHERE user_id=?", (user_id,))
        row = cur.fetchone()
        if row:
            data = _parse_session_data(row["data"])
            frozen = bool(data.get("frozen"))
            last_activity_at = data.get("last_activity_at") if isinstance(data.get("last_activity_at"), str) else None
            raw_cw = data.get("chatwoot_conversation_id")
            if raw_cw is not None and str(raw_cw).strip():
                chatwoot_conversation_id = str(raw_cw).strip()
            hist = data.get("history") or []
            if isinstance(hist, list):
                for h in hist:
                    if isinstance(h, dict):
                        messages.append(
                            MessageOut(role=str(h.get("role", "")), text=str(h.get("text", "")), created_at=None)
                        )
        if _table_exists(ro, "memory_facts"):
            cur = ro.execute(
                "SELECT fact_type, fact_key, fact_value, last_seen_at FROM memory_facts WHERE user_id=? ORDER BY id",
                (user_id,),
            )
            for ft, fk, fv, ls in cur.fetchall():
                facts.append(MemoryFactOut(fact_type=str(ft), fact_key=str(fk), fact_value=str(fv), last_seen_at=str(ls) if ls else None))
    finally:
        ro.close()
    return ConversationDetailOut(
        user_id=user_id,
        frozen=frozen,
        last_activity_at=last_activity_at,
        messages=messages,
        facts=facts,
        tags=tags,
        chatwoot_conversation_id=chatwoot_conversation_id,
    )


_KAI_REPLY_SCRIPT = Path(__file__).resolve().parents[1] / "kai_reply.py"
_KAI_CHATWOOT_SCRIPT = Path(__file__).resolve().parents[1] / "kai_chatwoot_studio.py"


def _run_chatwoot_tool(tenant: Tenant, payload: dict[str, Any]) -> dict[str, Any]:
    env = {**os.environ, "KAI_HOME": tenant.workspace_home}
    py_path = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = os.pathsep.join([str(KAI_REPO), py_path]) if py_path else str(KAI_REPO)
    try:
        result = subprocess.run(
            [sys.executable, str(_KAI_CHATWOOT_SCRIPT), tenant.workspace_home],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            timeout=45,
            cwd=str(KAI_REPO),
            env=env,
        )
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(status_code=504, detail="Chatwoot request timed out") from exc

    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "chatwoot_tool_failed").strip()[:500]
        raise HTTPException(status_code=502, detail=detail)

    try:
        out = json.loads((result.stdout or "").strip() or "{}")
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=502, detail="Invalid Chatwoot worker output") from exc

    if not out.get("ok"):
        raise HTTPException(status_code=400, detail=str(out.get("error") or "chatwoot_failed"))
    return out


@router.get("/{tenant_id}/inbox/chatwoot/account-labels", response_model=ChatwootAccountLabelsOut)
def list_chatwoot_account_labels(
    tenant_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tenant = _assert_tenant_member(tenant_id, user, db)
    out = _run_chatwoot_tool(tenant, {"action": "account_labels"})
    return ChatwootAccountLabelsOut(items=list(out.get("items") or []))


@router.get("/{tenant_id}/inbox/conversations/{user_id:path}/chatwoot", response_model=ChatwootMetaOut)
def get_chatwoot_meta(
    tenant_id: str,
    user_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tenant = _assert_tenant_member(tenant_id, user, db)
    out = _run_chatwoot_tool(tenant, {"action": "get_meta", "user_id": user_id})
    return ChatwootMetaOut(
        configured=bool(out.get("configured")),
        conversation_id=out.get("conversation_id"),
        status=out.get("status"),
        labels=list(out.get("labels") or []),
    )


@router.post("/{tenant_id}/inbox/conversations/{user_id:path}/chatwoot/status")
def set_chatwoot_status(
    tenant_id: str,
    user_id: str,
    body: ChatwootStatusBody,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tenant = _assert_tenant_member(tenant_id, user, db)
    payload: dict[str, Any] = {"action": "set_status", "user_id": user_id, "status": body.status}
    if body.snoozed_until is not None:
        payload["snoozed_until"] = body.snoozed_until
    _run_chatwoot_tool(tenant, payload)
    return {"ok": True}


@router.post("/{tenant_id}/inbox/conversations/{user_id:path}/chatwoot/private-note")
def post_chatwoot_private_note(
    tenant_id: str,
    user_id: str,
    body: ChatwootPrivateNoteBody,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tenant = _assert_tenant_member(tenant_id, user, db)
    _run_chatwoot_tool(tenant, {"action": "private_note", "user_id": user_id, "text": body.text})
    return {"ok": True}


@router.put("/{tenant_id}/inbox/conversations/{user_id:path}/chatwoot/labels")
def put_chatwoot_labels(
    tenant_id: str,
    user_id: str,
    body: ChatwootLabelsBody,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tenant = _assert_tenant_member(tenant_id, user, db)
    out = _run_chatwoot_tool(tenant, {"action": "set_labels", "user_id": user_id, "labels": body.labels})
    return {"ok": True, "labels": out.get("labels", [])}


@router.post("/{tenant_id}/inbox/conversations/{user_id:path}/chatwoot/handover")
def post_chatwoot_handover(
    tenant_id: str,
    user_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tenant = _assert_tenant_member(tenant_id, user, db)
    _run_chatwoot_tool(tenant, {"action": "human_handover", "user_id": user_id})
    return {"ok": True}


@router.post("/{tenant_id}/inbox/conversations/{user_id:path}/chatwoot/resume-bot")
def post_resume_bot(
    tenant_id: str,
    user_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tenant = _assert_tenant_member(tenant_id, user, db)
    _run_chatwoot_tool(tenant, {"action": "resume_bot", "user_id": user_id})
    return {"ok": True}


def _send_studio_reply(tenant: Tenant, user_id: str, text: str) -> dict[str, Any]:
    """Run kai_reply.py with tenant KAI_HOME so session + optional Chatwoot stay in sync."""
    _, path = _open_sessions_ro(tenant)
    if path and not path.is_file():
        raise HTTPException(
            status_code=503,
            detail=f"No sessions database yet at {path}. Run the bot once to create sessions.",
        )

    env = {**os.environ, "KAI_HOME": tenant.workspace_home}
    py_path = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = os.pathsep.join([str(KAI_REPO), py_path]) if py_path else str(KAI_REPO)

    try:
        result = subprocess.run(
            [sys.executable, str(_KAI_REPLY_SCRIPT), tenant.workspace_home, user_id, text],
            capture_output=True,
            text=True,
            timeout=45,
            cwd=str(KAI_REPO),
            env=env,
        )
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(status_code=504, detail="Reply timed out") from exc

    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "reply_failed").strip()[:500]
        raise HTTPException(status_code=502, detail=f"Failed to send reply: {detail}")

    try:
        payload = json.loads((result.stdout or "").strip() or "{}")
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=502, detail="Invalid reply worker output") from exc

    if not payload.get("ok"):
        raise HTTPException(status_code=502, detail=str(payload.get("error") or "reply_failed"))
    return payload


@router.post("/{tenant_id}/inbox/conversations/{user_id:path}/reply", response_model=ReplyOut)
def reply_to_conversation(
    tenant_id: str,
    user_id: str,
    body: ReplyCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tenant = _assert_tenant_member(tenant_id, user, db)
    payload = _send_studio_reply(tenant, user_id, body.text)
    return ReplyOut(
        ok=True,
        message=MessageOut(role="agent", text=body.text, created_at=None),
        chatwoot_delivered=bool(payload.get("chatwoot_delivered")),
        chatwoot_error=payload.get("chatwoot_error"),
        chatwoot_conversation_id=payload.get("chatwoot_conversation_id"),
    )


@router.get("/{tenant_id}/contacts", response_model=ContactListOut)
def list_contacts(
    tenant_id: str,
    search: str | None = None,
    tag: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tenant = _assert_tenant_member(tenant_id, user, db)
    ro, path = _open_sessions_ro(tenant)
    if ro is None:
        raise HTTPException(
            status_code=503,
            detail=f"No sessions database yet at {path}. Run the bot once to create sessions.",
        )
    user_ids: set[str] = set()
    session_meta: dict[str, dict[str, Any]] = {}
    facts_by_user: dict[str, list[MemoryFactOut]] = {}

    try:
        cur = ro.execute("SELECT user_id, data FROM sessions")
        for row in cur.fetchall():
            uid = row["user_id"]
            user_ids.add(uid)
            data = _parse_session_data(row["data"])
            session_meta[uid] = {
                "frozen": bool(data.get("frozen")),
                "last_activity_at": data.get("last_activity_at") if isinstance(data.get("last_activity_at"), str) else None,
            }
        if _table_exists(ro, "memory_facts"):
            cur = ro.execute("SELECT DISTINCT user_id FROM memory_facts")
            for (uid,) in cur.fetchall():
                user_ids.add(str(uid))
            cur = ro.execute(
                "SELECT user_id, fact_type, fact_key, fact_value, last_seen_at FROM memory_facts ORDER BY user_id, id"
            )
            for uid, ft, fk, fv, ls in cur.fetchall():
                facts_by_user.setdefault(str(uid), []).append(
                    MemoryFactOut(
                        fact_type=str(ft),
                        fact_key=str(fk),
                        fact_value=str(fv),
                        last_seen_at=str(ls) if ls else None,
                    )
                )
    finally:
        ro.close()

    tag_filter = (tag or "").strip().lower()
    tagged_users: set[str] | None = None
    if tag_filter:
        tagged_users = {
            r.user_id
            for r in db.query(ContactTag).filter(ContactTag.tenant_id == tenant_id, ContactTag.tag == tag_filter).all()
        }

    contacts: list[ContactOut] = []
    all_ids = sorted(user_ids, key=lambda u: session_meta.get(u, {}).get("last_activity_at") or "", reverse=True)
    for uid in all_ids:
        if tag_filter and uid not in (tagged_users or set()):
            continue
        facts = facts_by_user.get(uid, [])
        dn = _display_name_from_facts(facts) or uid
        if search:
            s = search.lower()
            if s not in uid.lower() and s not in dn.lower():
                hit = any(s in f.fact_value.lower() for f in facts)
                if not hit:
                    continue
        meta = session_meta.get(uid, {})
        tags_list = [r.tag for r in db.query(ContactTag).filter(ContactTag.tenant_id == tenant_id, ContactTag.user_id == uid).all()]
        preview = ""
        if facts:
            preview = f"{facts[0].fact_key}: {facts[0].fact_value}"[:100]
        contacts.append(
            ContactOut(
                user_id=uid,
                display_name=dn,
                last_activity_at=meta.get("last_activity_at"),
                frozen=bool(meta.get("frozen", False)),
                tags=sorted(set(tags_list)),
                fact_preview=preview,
            )
        )

    total = len(contacts)
    slice_c = contacts[offset : offset + max(1, min(limit, 200))]
    return ContactListOut(items=slice_c, total=total)


@router.get("/{tenant_id}/contacts/{user_id:path}", response_model=ContactDetailOut)
def get_contact(
    tenant_id: str,
    user_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    detail = get_conversation(tenant_id, user_id, user, db)
    dn = _display_name_from_facts(detail.facts) or user_id
    return ContactDetailOut(
        user_id=detail.user_id,
        display_name=dn,
        frozen=detail.frozen,
        last_activity_at=detail.last_activity_at,
        facts=detail.facts,
        tags=detail.tags,
    )


@router.post("/{tenant_id}/contacts/{user_id:path}/tags", status_code=status.HTTP_201_CREATED)
def add_contact_tag(
    tenant_id: str,
    user_id: str,
    body: TagCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _assert_tenant_member(tenant_id, user, db)
    tag = body.tag
    existing = (
        db.query(ContactTag)
        .filter(and_(ContactTag.tenant_id == tenant_id, ContactTag.user_id == user_id, ContactTag.tag == tag))
        .first()
    )
    if existing:
        return None
    db.add(
        ContactTag(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            user_id=user_id,
            tag=tag,
        )
    )
    db.commit()
    return None


@router.delete("/{tenant_id}/contacts/{user_id:path}/tags/{tag:path}", status_code=status.HTTP_204_NO_CONTENT)
def remove_contact_tag(
    tenant_id: str,
    user_id: str,
    tag: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _assert_tenant_member(tenant_id, user, db)
    db.query(ContactTag).filter(
        and_(ContactTag.tenant_id == tenant_id, ContactTag.user_id == user_id, ContactTag.tag == tag)
    ).delete()
    db.commit()
    return None
