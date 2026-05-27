from __future__ import annotations

import logging
from typing import Any

import requests

from kai.settings import Settings, get_settings

log = logging.getLogger("kai.chatwoot.client")


class ChatwootClient:
    """Shared Chatwoot REST client for outgoing messages and handover toggles."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._s = settings or get_settings()

    def is_configured(self) -> bool:
        return bool(
            (self._s.kai_chatwoot_api_base or "").strip()
            and (self._s.kai_chatwoot_api_token or "").strip()
            and (self._s.kai_chatwoot_account_id or "").strip()
        )

    def _headers(self) -> dict[str, str]:
        return {
            "api_access_token": (self._s.kai_chatwoot_api_token or "").strip(),
            "Content-Type": "application/json",
        }

    def _api_base(self) -> str:
        return (self._s.kai_chatwoot_api_base or "").rstrip("/")

    def _account_id(self) -> str:
        return (self._s.kai_chatwoot_account_id or "").strip()

    def create_outgoing_message(self, conversation_id: str, content: str) -> tuple[bool, str]:
        """Post a public outgoing message to a conversation."""
        conv_id = str(conversation_id or "").strip()
        text = (content or "").strip()
        if not conv_id:
            return False, "missing_conversation_id"
        if not text:
            return False, "empty_content"
        if not self.is_configured():
            return False, "chatwoot_not_configured"

        url = (
            f"{self._api_base()}/api/v1/accounts/{self._account_id()}"
            f"/conversations/{conv_id}/messages"
        )
        body: dict[str, Any] = {
            "content": text,
            "message_type": "outgoing",
            "private": False,
        }
        try:
            resp = requests.post(url, headers=self._headers(), json=body, timeout=25)
        except requests.RequestException as exc:
            log.warning("Chatwoot create_message failed conv=%s: %s", conv_id, exc)
            return False, f"request_failed:{exc.__class__.__name__}"
        if resp.status_code >= 300:
            return False, f"create_message_failed:{resp.status_code}"
        return True, ""

    def toggle_handover(self, conversation_id: str) -> tuple[bool, str]:
        """Switch conversation to human/live-agent mode (open, unassigned)."""
        conv_id = str(conversation_id or "").strip()
        if not conv_id:
            return False, "missing_conversation_id"
        if not self.is_configured():
            return False, "chatwoot_not_configured"

        headers = self._headers()
        base = self._api_base()
        account_id = self._account_id()

        url_toggle = f"{base}/api/v1/accounts/{account_id}/conversations/{conv_id}/toggle_status"
        try:
            r1 = requests.post(url_toggle, headers=headers, timeout=15)
        except requests.RequestException as exc:
            log.warning("Chatwoot toggle_status failed conv=%s: %s", conv_id, exc)
            return False, f"toggle_status_failed:{exc.__class__.__name__}"
        if r1.status_code >= 300:
            return False, f"toggle_status_failed:{r1.status_code}"

        url_update = f"{base}/api/v1/accounts/{account_id}/conversations/{conv_id}"
        try:
            r2 = requests.patch(
                url_update,
                headers=headers,
                json={"status": "open", "assignee_id": None},
                timeout=15,
            )
        except requests.RequestException as exc:
            log.warning("Chatwoot conversation_update failed conv=%s: %s", conv_id, exc)
            return False, f"conversation_update_failed:{exc.__class__.__name__}"
        if r2.status_code >= 300:
            return False, f"conversation_update_failed:{r2.status_code}"
        return True, ""
