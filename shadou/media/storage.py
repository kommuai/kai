"""Persist inbound media under SHADOU_HOME."""

from __future__ import annotations

import hashlib
import shutil
from datetime import datetime, timezone
from pathlib import Path

from shadou.media.config import get_media_config
from shadou.settings import get_settings


def _ext_for_mimetype(mimetype: str, modality: str) -> str:
    mt = (mimetype or "").split(";")[0].strip().lower()
    mapping = {
        "audio/ogg": "ogg",
        "audio/mpeg": "mp3",
        "audio/mp4": "m4a",
        "audio/amr": "amr",
        "audio/webm": "webm",
        "image/jpeg": "jpg",
        "image/png": "png",
        "image/webp": "webp",
    }
    if mt in mapping:
        return mapping[mt]
    if modality in ("voice", "audio"):
        return "ogg"
    if modality == "image":
        return "jpg"
    return "bin"


def media_root() -> Path:
    cfg = get_media_config()
    return get_settings().shadou_home / cfg.storage_dir


def store_inbound_media(
    *,
    source_path: Path,
    msg_id: str,
    modality: str,
    mimetype: str = "",
) -> Path:
    """Copy inbound media into tenant storage; return final path."""
    source_path = Path(source_path)
    if not source_path.is_file():
        raise FileNotFoundError(f"media_source_missing:{source_path}")

    cfg = get_media_config()
    if source_path.stat().st_size > cfg.max_bytes:
        raise ValueError("media_too_large")

    month = datetime.now(timezone.utc).strftime("%Y-%m")
    safe_id = hashlib.sha256((msg_id or source_path.name).encode()).hexdigest()[:16]
    ext = _ext_for_mimetype(mimetype, modality)
    dest_dir = media_root() / month
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{safe_id}.{ext}"
    shutil.copy2(source_path, dest)
    return dest
