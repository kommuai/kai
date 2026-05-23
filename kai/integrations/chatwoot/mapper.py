from __future__ import annotations

import logging
from typing import Any

from kai.lib.phone_identity import canonical_my_mobile

log = logging.getLogger("kai.chatwoot.mapper")


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _message_type_incoming(message: dict[str, Any]) -> bool:
    mt = message.get("message_type")
    if mt is None:
        return False
    if isinstance(mt, int):
        return mt == 0
    return str(mt).strip().lower() in {"incoming", "0"}


def _sender_type_contact(sender: dict[str, Any]) -> bool:
    st = str(sender.get("type") or "").strip().lower()
    if not st:
        return True
    return st in {"contact", "contacts"}


def should_skip_event(payload: dict[str, Any], *, allowed_inbox_ids: tuple[int, ...]) -> tuple[bool, str]:
    """Return (skip, reason). skip=True means do not process."""
    if not isinstance(payload, dict):
        return True, "invalid_payload"

    event = str(payload.get("event") or "").strip()
    if event and event != "message_created":
        return True, f"event_not_handled:{event}"

    message = _as_dict(payload.get("message"))
    if not message and payload.get("content") is not None:
        message = payload

    if not _message_type_incoming(message):
        return True, "not_incoming"

    if bool(message.get("private")):
        return True, "private_message"

    content = (message.get("content") or "").strip()
    if not content:
        return True, "empty_content"

    sender = _as_dict(message.get("sender"))
    if sender and not _sender_type_contact(sender):
        st = sender.get("type") or "unknown"
        return True, f"sender_not_contact:{st}"

    if allowed_inbox_ids:
        inbox = _as_dict(payload.get("inbox"))
        inbox_id = inbox.get("id")
        try:
            iid = int(inbox_id)
        except (TypeError, ValueError):
            return True, "inbox_not_allowed"
        if iid not in allowed_inbox_ids:
            return True, f"inbox_not_allowed:{iid}"

    return False, ""


def _first_str(*values: Any) -> str:
    for v in values:
        if v is None:
            continue
        s = str(v).strip()
        if s:
            return s
    return ""


def _resolve_phone(payload: dict[str, Any]) -> str:
    conversation = _as_dict(payload.get("conversation"))
    meta = _as_dict(conversation.get("meta"))
    meta_sender = _as_dict(meta.get("sender"))
    contact = _as_dict(conversation.get("contact"))
    top_contact = _as_dict(payload.get("contact"))
    message = _as_dict(payload.get("message"))

    raw = _first_str(
        meta_sender.get("phone_number"),
        contact.get("phone_number"),
        top_contact.get("phone_number"),
        message.get("source_id"),
        conversation.get("source_id"),
        meta_sender.get("identifier"),
        contact.get("identifier"),
        top_contact.get("identifier"),
    )

    if raw:
        canon = canonical_my_mobile(raw)
        return canon or raw

    fallback = _first_str(
        contact.get("id"),
        top_contact.get("id"),
        _as_dict(message.get("sender")).get("id"),
    )
    if fallback:
        log.warning("Chatwoot phone fallback to id=%s", fallback)
    return fallback


def map_chatwoot_event_to_agent_data(payload: dict[str, Any]) -> dict[str, Any] | None:
    """Map Agent Bot message_created payload to agent_message input dict."""
    conversation = _as_dict(payload.get("conversation"))
    message = _as_dict(payload.get("message"))
    if not message and payload.get("content"):
        message = payload

    conv_id = conversation.get("id") or payload.get("conversation_id")
    phone = _resolve_phone(payload)
    content = (message.get("content") or "").strip()

    if not phone:
        log.warning("Chatwoot mapper: no phone_number conv=%s", conv_id)
        return None
    if not content:
        return None

    out: dict[str, Any] = {
        "phone_number": phone,
        "content": content,
        "conversation_id": conv_id,
    }
    if message.get("id") is not None:
        out["chatwoot_message_id"] = message.get("id")
    return out
