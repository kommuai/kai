from __future__ import annotations

from typing import Any

from kai.settings import get_settings


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
    import requests

    conv_id = extract_chatwoot_conversation_id(payload)
    if not conv_id:
        return False, "missing_conversation_id"
    s = get_settings()
    api_base = (s.kai_chatwoot_api_base or "").strip()
    api_token = (s.kai_chatwoot_api_token or "").strip()
    account_id = (s.kai_chatwoot_account_id or "").strip()
    if not (api_base and api_token and account_id):
        return False, "chatwoot_not_configured"

    headers = {"api_access_token": api_token, "Content-Type": "application/json"}
    base = api_base.rstrip("/")

    url_toggle = f"{base}/api/v1/accounts/{account_id}/conversations/{conv_id}/toggle_status"
    r1 = requests.post(url_toggle, headers=headers, timeout=15)
    if r1.status_code >= 300:
        return False, f"toggle_status_failed:{r1.status_code}"

    url_update = f"{base}/api/v1/accounts/{account_id}/conversations/{conv_id}"
    r2 = requests.patch(url_update, headers=headers, json={"status": "open", "assignee_id": None}, timeout=15)
    if r2.status_code >= 300:
        return False, f"conversation_update_failed:{r2.status_code}"

    return True, ""
