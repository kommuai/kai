from __future__ import annotations

import json
import os
from pathlib import Path
import re
import requests

from config import AGENT_WORKSPACE
from support_runtime.models import RuntimeResult


TOOLS_PATH = Path(AGENT_WORKSPACE) / "compiled" / "tool_policies.json"


def _extract_entity(text: str, key: str) -> str:
    if key == "order_id":
        m = re.search(r"\b(?:order|ord)[-_ ]?([a-z0-9]{4,16})\b", text.lower())
        return m.group(1) if m else ""
    if key == "tracking_id":
        m = re.search(r"\b(?:track|trk)[-_ ]?([a-z0-9]{4,20})\b", text.lower())
        return m.group(1) if m else ""
    if key == "payment_ref":
        m = re.search(r"\b(?:pay|payment)[-_ ]?([a-z0-9]{4,20})\b", text.lower())
        return m.group(1) if m else ""
    return ""


class ToolPolicyEngine:
    def __init__(self) -> None:
        self.policies: dict = {}

    def load(self) -> None:
        if TOOLS_PATH.exists():
            self.policies = json.loads(TOOLS_PATH.read_text(encoding="utf-8"))
        else:
            self.policies = {}

    def decide(self, route_type: str, text: str) -> tuple[str, list[str]]:
        if route_type != "account_order_status_intent":
            return "", []
        lower = text.lower()
        if "shipment" in lower or "tracking" in lower:
            policy = self.policies.get("shipment_tracking", {})
        elif "payment" in lower:
            policy = self.policies.get("payment_verification", {})
        else:
            policy = self.policies.get("order_status", {})
        return policy.get("tool_name", ""), policy.get("required_entities", [])

    def _call_live_tool(self, tool_name: str, text: str) -> tuple[bool, str]:
        base = os.getenv("KAI_TOOL_BASE_URL", "").strip()
        token = os.getenv("KAI_TOOL_TOKEN", "").strip()
        if not base:
            return False, "tool_base_url_missing"
        try:
            resp = requests.post(
                f"{base.rstrip('/')}/{tool_name}",
                json={"query": text},
                headers={"Authorization": f"Bearer {token}"} if token else {},
                timeout=8,
            )
            if not resp.ok:
                return False, f"tool_http_{resp.status_code}"
            payload = resp.json()
            return True, payload.get("answer", "Tool completed.")
        except Exception as exc:  # noqa: BLE001
            return False, f"tool_call_failed:{exc}"

    def execute_or_clarify(self, tool_name: str, required_entities: list[str], text: str) -> RuntimeResult:
        missing = [e for e in required_entities if not _extract_entity(text, e)]
        if missing:
            m = ", ".join(missing)
            return RuntimeResult(
                decision="clarifying_question",
                answer=f"To proceed, please provide: {m}.",
                confidence=0.85,
                tool_needed=True,
                escalate_needed=False,
                capability_used="tool_policy",
            )
        ok, tool_answer = self._call_live_tool(tool_name, text)
        if ok:
            return RuntimeResult(
                decision="direct_answer",
                answer=tool_answer,
                confidence=0.92,
                tool_needed=True,
                escalate_needed=False,
                capability_used="tool_policy",
            )
        return RuntimeResult(
            decision="tool_use",
            answer=f"{tool_name} requested but unavailable ({tool_answer}). Escalating to support with captured details.",
            confidence=0.9,
            tool_needed=True,
            escalate_needed=True,
            capability_used="tool_policy",
        )
