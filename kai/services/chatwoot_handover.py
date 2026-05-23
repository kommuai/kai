from __future__ import annotations

from typing import Any

from kai.integrations.chatwoot.client import ChatwootClient


def extract_chatwoot_conversation_id(payload: dict[str, Any]) -> str:
    """Resolve Chatwoot conversation id from n8n / webhook payload."""
    for key in ("conversation_id", "chatwoot_conversation_id", "cw_conversation_id"):
        value = payload.get(key)
        if value:
            return str(value)
    conv = payload.get("conversation") or {}
    if isinstance(conv, dict) and conv.get("id"):
        return str(conv["id"])
    return ""


def enforce_live_agent_handover(payload: dict[str, Any]) -> tuple[bool, str]:
    """Switch Chatwoot conversation into human/live-agent mode."""
    conv_id = extract_chatwoot_conversation_id(payload)
    if not conv_id:
        return False, "missing_conversation_id"
    return ChatwootClient().toggle_handover(conv_id)
