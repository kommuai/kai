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

    def get_conversation(self, conversation_id: str) -> tuple[dict[str, Any] | None, str]:
        """Fetch conversation JSON (status, meta, etc.)."""
        conv_id = str(conversation_id or "").strip()
        if not conv_id:
            return None, "missing_conversation_id"
        if not self.is_configured():
            return None, "chatwoot_not_configured"
        url = f"{self._api_base()}/api/v1/accounts/{self._account_id()}/conversations/{conv_id}"
        try:
            resp = requests.get(url, headers=self._headers(), timeout=20)
        except requests.RequestException as exc:
            log.warning("Chatwoot get_conversation failed conv=%s: %s", conv_id, exc)
            return None, f"request_failed:{exc.__class__.__name__}"
        if resp.status_code >= 300:
            return None, f"get_conversation_failed:{resp.status_code}"
        try:
            return resp.json(), ""
        except ValueError:
            return None, "invalid_json_response"

    def set_conversation_status(
        self,
        conversation_id: str,
        status: str,
        *,
        snoozed_until: int | None = None,
    ) -> tuple[bool, str]:
        """Set conversation status (open / resolved / pending / snoozed)."""
        conv_id = str(conversation_id or "").strip()
        st = (status or "").strip().lower()
        if not conv_id:
            return False, "missing_conversation_id"
        if st not in {"open", "resolved", "pending", "snoozed"}:
            return False, "invalid_status"
        if not self.is_configured():
            return False, "chatwoot_not_configured"

        body: dict[str, Any] = {"status": st}
        if snoozed_until is not None and st == "snoozed":
            body["snoozed_until"] = int(snoozed_until)

        url = f"{self._api_base()}/api/v1/accounts/{self._account_id()}/conversations/{conv_id}/toggle_status"
        try:
            resp = requests.post(url, headers=self._headers(), json=body, timeout=20)
        except requests.RequestException as exc:
            log.warning("Chatwoot toggle_status failed conv=%s: %s", conv_id, exc)
            return False, f"toggle_status_failed:{exc.__class__.__name__}"
        if resp.status_code >= 300:
            return False, f"toggle_status_failed:{resp.status_code}"
        return True, ""

    def create_private_note(self, conversation_id: str, content: str) -> tuple[bool, str]:
        """Post an internal-only note (not sent to the contact)."""
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
            "private": True,
        }
        try:
            resp = requests.post(url, headers=self._headers(), json=body, timeout=25)
        except requests.RequestException as exc:
            log.warning("Chatwoot private_note failed conv=%s: %s", conv_id, exc)
            return False, f"request_failed:{exc.__class__.__name__}"
        if resp.status_code >= 300:
            return False, f"private_note_failed:{resp.status_code}"
        return True, ""

    def get_conversation_labels(self, conversation_id: str) -> tuple[list[str], str]:
        """Return label titles/slugs attached to the conversation."""
        conv_id = str(conversation_id or "").strip()
        if not conv_id:
            return [], "missing_conversation_id"
        if not self.is_configured():
            return [], "chatwoot_not_configured"
        url = f"{self._api_base()}/api/v1/accounts/{self._account_id()}/conversations/{conv_id}/labels"
        try:
            resp = requests.get(url, headers=self._headers(), timeout=15)
        except requests.RequestException as exc:
            log.warning("Chatwoot get_labels failed conv=%s: %s", conv_id, exc)
            return [], f"request_failed:{exc.__class__.__name__}"
        if resp.status_code >= 300:
            return [], f"get_labels_failed:{resp.status_code}"
        try:
            data = resp.json()
        except ValueError:
            return [], "invalid_json_response"
        raw = data.get("payload") if isinstance(data, dict) else None
        if isinstance(raw, list):
            return [str(x).strip() for x in raw if str(x).strip()], ""
        return [], ""

    def set_conversation_labels(self, conversation_id: str, labels: list[str]) -> tuple[bool, str]:
        """Replace all conversation labels (Chatwoot overwrites the full list)."""
        conv_id = str(conversation_id or "").strip()
        if not conv_id:
            return False, "missing_conversation_id"
        if not self.is_configured():
            return False, "chatwoot_not_configured"
        lab = [str(x).strip() for x in labels if str(x).strip()]
        url = f"{self._api_base()}/api/v1/accounts/{self._account_id()}/conversations/{conv_id}/labels"
        body = {"labels": lab}
        try:
            resp = requests.post(url, headers=self._headers(), json=body, timeout=20)
        except requests.RequestException as exc:
            log.warning("Chatwoot set_labels failed conv=%s: %s", conv_id, exc)
            return False, f"request_failed:{exc.__class__.__name__}"
        if resp.status_code >= 300:
            return False, f"set_labels_failed:{resp.status_code}"
        return True, ""

    def list_account_labels(self) -> tuple[list[dict[str, Any]], str]:
        """List label definitions for the account (picker in Studio)."""
        if not self.is_configured():
            return [], "chatwoot_not_configured"
        url = f"{self._api_base()}/api/v1/accounts/{self._account_id()}/labels"
        try:
            resp = requests.get(url, headers=self._headers(), timeout=20)
        except requests.RequestException as exc:
            log.warning("Chatwoot list_account_labels failed: %s", exc)
            return [], f"request_failed:{exc.__class__.__name__}"
        if resp.status_code >= 300:
            return [], f"list_labels_failed:{resp.status_code}"
        try:
            data = resp.json()
        except ValueError:
            return [], "invalid_json_response"
        if isinstance(data, list):
            return [x for x in data if isinstance(x, dict)], ""
        if isinstance(data, dict) and isinstance(data.get("payload"), list):
            return [x for x in data["payload"] if isinstance(x, dict)], ""
        return [], ""
