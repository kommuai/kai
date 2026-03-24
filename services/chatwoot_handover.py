from __future__ import annotations

from typing import Any

import requests

from config import KAI_CHATWOOT_ACCOUNT_ID, KAI_CHATWOOT_API_BASE, KAI_CHATWOOT_API_TOKEN


def _extract_conversation_id(payload: dict[str, Any]) -> str:
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
    conv_id = _extract_conversation_id(payload)
    if not conv_id:
        return False, "missing_conversation_id"
    if not (KAI_CHATWOOT_API_BASE and KAI_CHATWOOT_API_TOKEN and KAI_CHATWOOT_ACCOUNT_ID):
        return False, "chatwoot_not_configured"

    headers = {"api_access_token": KAI_CHATWOOT_API_TOKEN, "Content-Type": "application/json"}
    base = KAI_CHATWOOT_API_BASE.rstrip("/")

    # 1) Mark as open for human handling.
    url_toggle = f"{base}/api/v1/accounts/{KAI_CHATWOOT_ACCOUNT_ID}/conversations/{conv_id}/toggle_status"
    r1 = requests.post(url_toggle, headers=headers, timeout=15)
    if r1.status_code >= 300:
        return False, f"toggle_status_failed:{r1.status_code}"

    # 2) Ensure bot no longer owns the conversation.
    url_update = f"{base}/api/v1/accounts/{KAI_CHATWOOT_ACCOUNT_ID}/conversations/{conv_id}"
    r2 = requests.patch(url_update, headers=headers, json={"status": "open", "assignee_id": None}, timeout=15)
    if r2.status_code >= 300:
        return False, f"conversation_update_failed:{r2.status_code}"

    return True, ""
