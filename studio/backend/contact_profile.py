"""Resolve inbox correspondent display name and phone from session user_id + memory facts."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from schemas import MemoryFactOut

_DIGITS = re.compile(r"\D+")


def _digits(raw: str) -> str:
    return _DIGITS.sub("", raw or "")


def format_phone_display(raw: str) -> str | None:
    """Format a plausible mobile number for display, or None if not phone-like."""
    d = _digits(raw)
    if len(d) < 9 or len(d) > 15:
        return None
    if d.startswith("60") and 10 <= len(d) <= 12:
        return f"+{d}"
    if d.startswith("0") and len(d) in (10, 11):
        return f"+60{d[1:]}"
    if len(d) >= 10:
        return f"+{d}"
    return None


def is_internal_whatsapp_id(user_id: str) -> bool:
    """True for WhatsApp @lid-style keys that are not a normal MSISDN."""
    if format_phone_display(user_id):
        d = _digits(user_id)
        if d.startswith("60") and len(d) <= 12:
            return False
        if d.startswith("0") and len(d) <= 11:
            return False
    d = _digits(user_id)
    return len(d) >= 14


def _whatsapp_handle_from_facts(facts: list[MemoryFactOut]) -> str:
    """WhatsApp profile / push name (what the WA app shows in the chat list)."""
    priority_keys = ("wa_push_name", "push_name", "verified_name", "wa_verified_name")
    by_key: dict[str, str] = {}
    for f in facts:
        if f.fact_type != "identity":
            continue
        fk = f.fact_key.lower()
        v = (f.fact_value or "").strip()
        if v:
            by_key[fk] = v
    for key in priority_keys:
        if by_key.get(key):
            return by_key[key]
    return ""


def _chat_extracted_name_from_facts(facts: list[MemoryFactOut]) -> str:
    """Name inferred from conversation (lower priority than WhatsApp handle)."""
    for f in facts:
        if f.fact_type != "identity":
            continue
        fk = f.fact_key.lower()
        if fk in ("name", "display_name", "full_name"):
            v = (f.fact_value or "").strip()
            if v:
                return v
    return ""


def load_whatsapp_contact_directory(tenant_home: Path | None) -> dict[str, dict[str, str]]:
    if not tenant_home:
        return {}
    path = tenant_home / "data" / "whatsapp" / "contact-directory.json"
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            return raw
    except (json.JSONDecodeError, OSError):
        pass
    return {}


def correspondent_profile(
    user_id: str,
    facts: list[MemoryFactOut],
    *,
    directory: dict[str, dict[str, str]] | None = None,
) -> dict[str, str | None]:
    """
    Returns display_name (prefer WhatsApp handle), phone (formatted), user_id.
    """
    uid = (user_id or "").strip()
    phone: str | None = None

    for f in facts:
        fk = f.fact_key.lower()
        if fk in ("wa_phone", "phone", "mobile"):
            p = format_phone_display(f.fact_value)
            if p and not is_internal_whatsapp_id(f.fact_value):
                phone = p
        elif f.fact_type == "device_account" and fk == "phone_number":
            # Kai stores session key here; skip @lid internal ids.
            if not is_internal_whatsapp_id(f.fact_value):
                p = format_phone_display(f.fact_value)
                if p:
                    phone = p

    if not phone and directory:
        entry = directory.get(uid) or {}
        p = format_phone_display(str(entry.get("phone") or ""))
        if p:
            phone = p

    if not phone:
        p = format_phone_display(uid)
        if p and not is_internal_whatsapp_id(uid):
            phone = p

    handle = _whatsapp_handle_from_facts(facts)
    name = handle or _chat_extracted_name_from_facts(facts)
    if not name:
        if is_internal_whatsapp_id(uid):
            tail = uid[-6:] if len(uid) >= 6 else uid
            name = f"WhatsApp …{tail}"
        elif phone:
            name = phone
        else:
            name = uid or "Unknown"

    return {
        "user_id": uid,
        "display_name": name,
        "phone": phone,
    }


def _table_exists(conn: Any, name: str) -> bool:
    cur = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type IN ('table','virtual') AND name=? LIMIT 1",
        (name,),
    )
    return cur.fetchone() is not None


def load_facts_by_user(conn: Any) -> dict[str, list[MemoryFactOut]]:
    """Batch-load memory_facts grouped by user_id."""
    out: dict[str, list[MemoryFactOut]] = {}
    if not _table_exists(conn, "memory_facts"):
        return out
    cur = conn.execute(
        "SELECT user_id, fact_type, fact_key, fact_value, last_seen_at FROM memory_facts ORDER BY user_id, id"
    )
    for uid, ft, fk, fv, ls in cur.fetchall():
        out.setdefault(str(uid), []).append(
            MemoryFactOut(
                fact_type=str(ft),
                fact_key=str(fk),
                fact_value=str(fv),
                last_seen_at=str(ls) if ls else None,
            )
        )
    return out
