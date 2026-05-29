"""WhatsApp Baileys QR linking during onboarding and per-tenant."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from channel_config import apply_channel_to_workspace, get_channel_status, save_channel_meta
from database import get_db
from deps import get_current_user
from models import User
from onboarding_service import _assert_session_owner, _session_dir
from routers.tenants_router import _assert_tenant_member
from whatsapp_bridge_client import link_status, start_link, stop_link
from whatsapp_worker import enrich_channel_status, global_worker_status

router = APIRouter(prefix="/tenants", tags=["whatsapp"])

_META = ".whatsapp-link.json"


def _meta_path(base: Path) -> Path:
    return base / _META


def _read_meta(base: Path) -> dict[str, Any]:
    p = _meta_path(base)
    if not p.is_file():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8")) or {}
    except json.JSONDecodeError:
        return {}


def _write_meta(base: Path, data: dict[str, Any]) -> None:
    base.mkdir(parents=True, exist_ok=True)
    _meta_path(base).write_text(json.dumps(data, indent=2), encoding="utf-8")


def _auth_dir_onboarding(user_id: str, session_id: str) -> Path:
    return _session_dir(user_id, session_id) / "whatsapp" / "baileys-auth"


def _auth_dir_tenant(home: Path) -> Path:
    return home / "data" / "whatsapp" / "baileys-auth"


def _resume_or_start_link(meta: dict[str, Any], auth_dir: Path) -> dict[str, Any]:
    """Reuse in-flight link session so QR scan is not invalidated by a second start."""
    link_id = meta.get("link_id")
    if link_id:
        try:
            result = link_status(str(link_id))
            st = (result.get("status") or "").lower()
            if st in ("starting", "qr", "connecting", "connected"):
                return {**result, "link_id": link_id}
        except HTTPException as exc:
            if exc.status_code != 404:
                raise
    result = start_link(str(auth_dir))
    return result


@router.get("/whatsapp-worker")
def whatsapp_worker_overview(user: User = Depends(get_current_user)):
    """Global bridge + worker status for dashboard."""
    return global_worker_status()


@router.get("/{tenant_id}/channels")
def tenant_channels(
    tenant_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    t = _assert_tenant_member(tenant_id, user, db)
    status = get_channel_status(Path(t.workspace_home).resolve())
    return enrich_channel_status(status, t.slug)


@router.post("/onboarding/sessions/{session_id}/whatsapp/start")
def onboarding_whatsapp_start(
    session_id: str,
    user: User = Depends(get_current_user),
):
    base = _assert_session_owner(user.id, session_id)
    auth_dir = _auth_dir_onboarding(user.id, session_id)
    meta = _read_meta(base)
    result = _resume_or_start_link(meta, auth_dir)
    _write_meta(
        base,
        {
            "link_id": result.get("link_id"),
            "auth_dir": str(auth_dir),
            "phone": result.get("phone"),
            "status": result.get("status"),
        },
    )
    return result


@router.get("/onboarding/sessions/{session_id}/whatsapp/status")
def onboarding_whatsapp_status(
    session_id: str,
    user: User = Depends(get_current_user),
):
    base = _assert_session_owner(user.id, session_id)
    meta = _read_meta(base)
    link_id = meta.get("link_id")
    if not link_id:
        return {"status": "idle", "qr_data_url": None, "phone": None, "error": None}
    result = link_status(str(link_id))
    if result.get("status") == "connected" and result.get("phone"):
        meta["phone"] = result["phone"]
        meta["status"] = "connected"
        _write_meta(base, meta)
    return result


@router.post("/{tenant_id}/whatsapp/start")
def tenant_whatsapp_start(
    tenant_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    t = _assert_tenant_member(tenant_id, user, db)
    home = Path(t.workspace_home).resolve()
    auth_dir = _auth_dir_tenant(home)
    result = start_link(str(auth_dir))
    _write_meta(
        home,
        {
            "link_id": result.get("link_id"),
            "phone": result.get("phone"),
            "status": result.get("status"),
        },
    )
    return result


@router.get("/{tenant_id}/whatsapp/status")
def tenant_whatsapp_status(
    tenant_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    t = _assert_tenant_member(tenant_id, user, db)
    home = Path(t.workspace_home).resolve()
    meta = _read_meta(home)
    link_id = meta.get("link_id")
    if not link_id:
        return {"status": "idle", "qr_data_url": None, "phone": None, "error": None}
    result = link_status(str(link_id))
    if result.get("status") == "connected":
        phone = result.get("phone") or ""
        meta["phone"] = phone
        meta["status"] = "connected"
        _write_meta(home, meta)
        apply_channel_to_workspace(home, "whatsapp_baileys", whatsapp_phone=phone)
        save_channel_meta(home, "whatsapp_baileys", whatsapp_phone=phone)
        lid = meta.get("link_id")
        if lid:
            stop_link(str(lid))
    return result
