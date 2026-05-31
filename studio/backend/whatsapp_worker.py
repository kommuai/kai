"""Bridge worker health for Studio UI (live vs configured-only)."""
from __future__ import annotations

import time
from typing import Any

from whatsapp_bridge_client import BRIDGE_BASE, fetch_bridge_health

_HEALTH_CACHE: dict[str, Any] = {"at": 0.0, "data": None}
_CACHE_TTL_SEC = 3.0


def get_bridge_health_cached() -> dict[str, Any] | None:
    now = time.monotonic()
    if now - float(_HEALTH_CACHE["at"]) < _CACHE_TTL_SEC and _HEALTH_CACHE["data"] is not None:
        return _HEALTH_CACHE["data"]
    data = fetch_bridge_health()
    _HEALTH_CACHE["at"] = now
    _HEALTH_CACHE["data"] = data
    return data


def worker_tenant_by_slug(slug: str, health: dict[str, Any] | None = None) -> dict[str, Any] | None:
    health = health if health is not None else get_bridge_health_cached()
    if not health:
        return None
    worker = health.get("worker")
    if not isinstance(worker, dict):
        return None
    tenants = worker.get("tenants")
    if not isinstance(tenants, list):
        return None
    slug_l = (slug or "").strip().lower()
    for row in tenants:
        if isinstance(row, dict) and str(row.get("slug") or "").lower() == slug_l:
            return row
    return None


def _delivery_label(
    *,
    configured: bool,
    auth_present: bool,
    bridge_reachable: bool,
    worker_enabled: bool,
    worker_state: str | None,
) -> str:
    if not auth_present and not configured:
        return "not_configured"
    if not bridge_reachable:
        return "bridge_offline"
    if not worker_enabled:
        return "worker_disabled"
    if configured and worker_state == "connected":
        return "live"
    if configured or auth_present:
        return "configured_only"
    return "not_configured"


def enrich_channel_status(status: dict[str, Any], tenant_slug: str) -> dict[str, Any]:
    health = get_bridge_health_cached()
    bridge_reachable = bool(health and health.get("ok") is True)
    worker = (health or {}).get("worker") if isinstance((health or {}).get("worker"), dict) else {}
    worker_enabled = bool(worker.get("enabled", True))

    wa = status.get("whatsapp_baileys")
    if not isinstance(wa, dict):
        wa = {}

    row = worker_tenant_by_slug(tenant_slug, health)
    worker_state = str(row.get("state") or "").lower() if row else None
    worker_error = row.get("error") if row else None

    configured = bool(wa.get("configured"))
    auth_present = bool(wa.get("auth_present"))
    worker_live = bridge_reachable and worker_enabled and worker_state == "connected"

    wa = {
        **wa,
        "worker_state": worker_state,
        "worker_error": worker_error,
        "worker_live": worker_live,
        "delivery": _delivery_label(
            configured=configured,
            auth_present=auth_present,
            bridge_reachable=bridge_reachable,
            worker_enabled=worker_enabled,
            worker_state=worker_state,
        ),
    }

    return {
        **status,
        "bridge_reachable": bridge_reachable,
        "bridge_url": BRIDGE_BASE,
        "worker_enabled": worker_enabled,
        "whatsapp_baileys": wa,
    }


def global_worker_status() -> dict[str, Any]:
    health = get_bridge_health_cached()
    bridge_reachable = bool(health and health.get("ok") is True)
    worker = (health or {}).get("worker") if isinstance((health or {}).get("worker"), dict) else {}
    tenants = worker.get("tenants") if isinstance(worker.get("tenants"), list) else []
    live_count = sum(
        1 for t in tenants if isinstance(t, dict) and str(t.get("state") or "").lower() == "connected"
    )
    return {
        "bridge_reachable": bridge_reachable,
        "bridge_url": BRIDGE_BASE,
        "worker_enabled": bool(worker.get("enabled", True)),
        "scan_interval_ms": worker.get("scan_interval_ms"),
        "tenants": tenants,
        "live_tenant_count": live_count,
        "detail": None
        if bridge_reachable
        else "WhatsApp bridge is not running. Start it with: systemctl --user start shadou-whatsapp-bridge.service",
    }
