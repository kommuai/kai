"""HTTP client for the Node Baileys whatsapp-bridge sidecar."""
from __future__ import annotations

import os
from typing import Any

import requests
from fastapi import HTTPException

BRIDGE_BASE = (os.getenv("WHATSAPP_BRIDGE_URL") or "http://127.0.0.1:18791").rstrip("/")
TIMEOUT = float(os.getenv("WHATSAPP_BRIDGE_TIMEOUT", "30"))


def _bridge_health_ok() -> bool:
    try:
        r = requests.get(f"{BRIDGE_BASE}/health", timeout=2)
        if not r.ok:
            return False
        data = r.json()
        return isinstance(data, dict) and data.get("ok") is True
    except Exception:
        return False


def bridge_reachable() -> bool:
    return _bridge_health_ok()


def fetch_bridge_health() -> dict[str, Any] | None:
    """Full GET /health JSON, or None if unreachable."""
    try:
        r = requests.get(f"{BRIDGE_BASE}/health", timeout=2)
        if not r.ok:
            return None
        data = r.json()
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def _bridge_unavailable_detail() -> str:
    if _bridge_health_ok():
        return ""
    try:
        r = requests.get(f"{BRIDGE_BASE}/health", timeout=2)
        if r.ok:
            return (
                f"Port {BRIDGE_BASE} responded but is not the Shadou WhatsApp bridge "
                "(expected JSON {{\"ok\": true}}). Set WHATSAPP_BRIDGE_URL to the bridge "
                "process (default http://127.0.0.1:18791) and run: cd studio/whatsapp-bridge && npm install && npm start"
            )
    except requests.RequestException:
        pass
    return (
        "WhatsApp bridge is not running. In a separate terminal run:\n"
        "  cd studio/whatsapp-bridge && npm install && npm start\n"
        f"Then ensure WHATSAPP_BRIDGE_URL is {BRIDGE_BASE} (default port 18791)."
    )


def start_link(auth_dir: str) -> dict[str, Any]:
    if not _bridge_health_ok():
        raise HTTPException(status_code=503, detail=_bridge_unavailable_detail())
    try:
        r = requests.post(
            f"{BRIDGE_BASE}/v1/link/start",
            json={"auth_dir": str(auth_dir)},
            timeout=TIMEOUT,
        )
    except requests.RequestException as exc:
        raise HTTPException(status_code=503, detail=_bridge_unavailable_detail()) from exc
    if not r.ok:
        body = (r.text or "")[:500]
        raise HTTPException(
            status_code=502,
            detail=f"WhatsApp bridge error ({r.status_code}): {body or 'start failed'}",
        )
    return r.json()


def link_status(link_id: str) -> dict[str, Any]:
    if not _bridge_health_ok():
        raise HTTPException(status_code=503, detail=_bridge_unavailable_detail())
    try:
        r = requests.get(f"{BRIDGE_BASE}/v1/link/{link_id}/status", timeout=TIMEOUT)
    except requests.RequestException as exc:
        raise HTTPException(status_code=503, detail=_bridge_unavailable_detail()) from exc
    if r.status_code == 404:
        raise HTTPException(status_code=404, detail="Link session expired; start again")
    if not r.ok:
        body = (r.text or "")[:500]
        raise HTTPException(
            status_code=502,
            detail=f"WhatsApp bridge error ({r.status_code}): {body or 'status failed'}",
        )
    return r.json()


def stop_link(link_id: str) -> None:
    try:
        requests.post(f"{BRIDGE_BASE}/v1/link/{link_id}/stop", timeout=5)
    except Exception:
        pass


def send_worker_message(tenant_slug: str, user_id: str, text: str) -> dict[str, Any]:
    """Deliver a Studio agent reply to the customer on WhatsApp (Baileys worker)."""
    if not _bridge_health_ok():
        raise HTTPException(status_code=503, detail=_bridge_unavailable_detail())
    try:
        r = requests.post(
            f"{BRIDGE_BASE}/v1/worker/send",
            json={
                "tenant_slug": tenant_slug,
                "user_id": user_id,
                "text": text,
            },
            timeout=TIMEOUT,
        )
    except requests.RequestException as exc:
        raise HTTPException(status_code=503, detail=_bridge_unavailable_detail()) from exc
    try:
        payload = r.json() if r.content else {}
    except ValueError:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    if not r.ok:
        err = payload.get("error") or payload.get("detail") or (r.text or "")[:500]
        raise HTTPException(
            status_code=r.status_code if 400 <= r.status_code < 600 else 502,
            detail=f"WhatsApp delivery failed: {err or 'send failed'}",
        )
    if not payload.get("ok"):
        raise HTTPException(
            status_code=502,
            detail=str(payload.get("error") or "WhatsApp delivery failed"),
        )
    return payload
