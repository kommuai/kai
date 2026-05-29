"""Write messaging channel settings into tenant workspace.yaml."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

CHANNEL_TYPES = frozenset({"none", "telegram", "whatsapp_cloud", "whatsapp_baileys"})
_STUDIO_CHANNEL_META = ".studio-channel.json"


def _meta_path(workspace_home: Path) -> Path:
    return workspace_home / _STUDIO_CHANNEL_META


def save_channel_meta(
    workspace_home: Path,
    channel_type: str,
    *,
    whatsapp_phone: str | None = None,
) -> None:
    """Persist intended channel so AI bootstrap / workspace edits can restore it."""
    workspace_home.mkdir(parents=True, exist_ok=True)
    payload = {
        "channel_type": (channel_type or "none").strip().lower(),
        "whatsapp_phone": (whatsapp_phone or "").strip() or None,
    }
    _meta_path(workspace_home).write_text(json.dumps(payload, indent=2), encoding="utf-8")


def reapply_saved_channel(workspace_home: Path) -> bool:
    """Re-apply channel blocks after workspace.yaml was replaced (e.g. AI bootstrap)."""
    p = _meta_path(workspace_home)
    if not p.is_file():
        return False
    try:
        meta = json.loads(p.read_text(encoding="utf-8")) or {}
    except json.JSONDecodeError:
        return False
    ct = (meta.get("channel_type") or "none").strip().lower()
    if ct == "none":
        return False
    phone = meta.get("whatsapp_phone")
    if not phone:
        phone = phone_from_baileys_auth(workspace_home)
    apply_channel_to_workspace(workspace_home, ct, whatsapp_phone=phone)
    return True


def phone_from_baileys_auth(workspace_home: Path) -> str | None:
    creds_path = workspace_home / "data" / "whatsapp" / "baileys-auth" / "creds.json"
    if not creds_path.is_file():
        return None
    try:
        creds = json.loads(creds_path.read_text(encoding="utf-8")) or {}
    except json.JSONDecodeError:
        return None
    me = creds.get("me") or {}
    raw = me.get("id") if isinstance(me, dict) else None
    if not raw:
        return None
    return str(raw).split(":")[0] or None


def baileys_auth_present(workspace_home: Path) -> bool:
    auth = workspace_home / "data" / "whatsapp" / "baileys-auth"
    return auth.is_dir() and (auth / "creds.json").is_file()


def get_channel_status(workspace_home: Path) -> dict[str, Any]:
    """Summary for Studio UI."""
    home = workspace_home.resolve()
    p = home / "workspace.yaml"
    data: dict[str, Any] = {}
    if p.is_file():
        loaded = yaml.safe_load(p.read_text(encoding="utf-8", errors="replace")) or {}
        if isinstance(loaded, dict):
            data = loaded

    channels = data.get("channels") if isinstance(data.get("channels"), dict) else {}
    inbound = channels.get("inbound") if isinstance(channels.get("inbound"), dict) else {}
    baileys = channels.get("whatsapp_baileys") if isinstance(channels.get("whatsapp_baileys"), dict) else {}

    provider = (inbound.get("provider") or "none").strip().lower()
    phone = (baileys.get("phone") or "").strip() or phone_from_baileys_auth(home)
    has_auth = baileys_auth_present(home)
    enabled = bool(baileys.get("enabled"))

    # Heal: credentials on disk but workspace never patched (common after document bootstrap).
    if has_auth and (not enabled or provider != "whatsapp_baileys"):
        if reapply_saved_channel(home):
            return get_channel_status(home)
        apply_channel_to_workspace(home, "whatsapp_baileys", whatsapp_phone=phone)
        save_channel_meta(home, "whatsapp_baileys", whatsapp_phone=phone)
        return get_channel_status(home)

    return {
        "inbound_provider": provider,
        "whatsapp_baileys": {
            "enabled": enabled,
            "phone": phone,
            "auth_present": has_auth,
            "configured": enabled and provider == "whatsapp_baileys" and has_auth,
        },
    }


def apply_channel_to_workspace(
    workspace_home: Path,
    channel_type: str,
    *,
    whatsapp_phone: str | None = None,
) -> None:
    """Patch workspace.yaml channels.inbound + provider blocks."""
    ct = (channel_type or "none").strip().lower()
    if ct not in CHANNEL_TYPES:
        ct = "none"

    phone = whatsapp_phone
    if ct == "whatsapp_baileys" and not phone:
        phone = phone_from_baileys_auth(workspace_home)

    save_channel_meta(workspace_home, ct, whatsapp_phone=phone)

    p = workspace_home / "workspace.yaml"
    data: dict[str, Any] = {}
    if p.is_file():
        loaded = yaml.safe_load(p.read_text(encoding="utf-8", errors="replace")) or {}
        if isinstance(loaded, dict):
            data = loaded

    channels = data.get("channels")
    if not isinstance(channels, dict):
        channels = {}
        data["channels"] = channels

    channels["inbound"] = {"provider": ct if ct != "none" else "none"}

    telegram = channels.get("telegram")
    if not isinstance(telegram, dict):
        telegram = {}
    telegram["enabled"] = ct == "telegram"
    channels["telegram"] = telegram

    cloud = channels.get("whatsapp_cloud")
    if not isinstance(cloud, dict):
        cloud = {}
    cloud["enabled"] = ct == "whatsapp_cloud"
    channels["whatsapp_cloud"] = cloud

    baileys = channels.get("whatsapp_baileys")
    if not isinstance(baileys, dict):
        baileys = {}
    if ct == "whatsapp_baileys":
        baileys["enabled"] = True
        baileys["auth_dir"] = "data/whatsapp/baileys-auth"
        if phone:
            baileys["phone"] = phone.strip()
    else:
        baileys["enabled"] = False
    channels["whatsapp_baileys"] = baileys

    p.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
