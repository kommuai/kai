import logging
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests

log = logging.getLogger(__name__)

META_TOKEN = os.getenv("META_PERMANENT_TOKEN", "")


def _media_cache_dir() -> Path:
    try:
        from kai.settings import get_settings

        return get_settings().kai_home / "data" / "media"
    except Exception:  # noqa: BLE001
        return Path("data/media")


def _db_path() -> str:
    try:
        from kai.settings import get_settings

        return get_settings().session_db_path
    except Exception:  # noqa: BLE001
        return os.getenv("DB_PATH", "data/sessions.db")


def init_media_log() -> None:
    """Ensure media_log table exists in the session database."""
    cache = _media_cache_dir()
    cache.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(_db_path())
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS media_log (
            id TEXT PRIMARY KEY,
            sender TEXT,
            type TEXT,
            caption TEXT,
            mime_type TEXT,
            path TEXT,
            created_at TEXT
        )
        """
    )
    conn.commit()
    conn.close()


def insert_media_record(media_id, sender, mtype, caption, mime, path) -> None:
    conn = sqlite3.connect(_db_path())
    cur = conn.cursor()
    cur.execute(
        "INSERT OR REPLACE INTO media_log VALUES (?, ?, ?, ?, ?, ?, ?)",
        (media_id, sender, mtype, caption, mime, path, datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()


def get_media_url(media_id: str) -> Optional[str]:
    if not META_TOKEN:
        log.error("META_PERMANENT_TOKEN missing")
        return None
    try:
        r = requests.get(
            f"https://graph.facebook.com/v17.0/{media_id}",
            headers={"Authorization": f"Bearer {META_TOKEN}"},
            timeout=15,
        )
        if r.ok:
            return r.json().get("url")
        log.warning("Failed to get media URL: %s", r.text)
    except Exception as exc:  # noqa: BLE001
        log.error("get_media_url error: %s", exc)
    return None


def guess_extension_from_type(mime_type: str) -> str:
    if "image" in mime_type:
        return ".jpg"
    if "audio" in mime_type:
        return ".ogg"
    if "video" in mime_type:
        return ".mp4"
    if "pdf" in mime_type:
        return ".pdf"
    return ".bin"


def download_media(media_url: str, media_id: str, ext: str) -> Optional[str]:
    try:
        headers = {"Authorization": f"Bearer {META_TOKEN}"}
        r = requests.get(media_url, headers=headers, timeout=30)
        if not r.ok:
            log.warning("Download failed %s", r.status_code)
            return None
        cache = _media_cache_dir()
        cache.mkdir(parents=True, exist_ok=True)
        path = str(cache / f"{media_id}{ext}")
        with open(path, "wb") as fh:
            fh.write(r.content)
        return path
    except Exception as exc:  # noqa: BLE001
        log.error("download_media error: %s", exc)
        return None


def handle_incoming_media(msg: dict, sender_id: str, add_message_to_history) -> bool:
    """Process WhatsApp media messages (optional; not wired on default chat route)."""
    msg_type = msg.get("type", "text")
    if msg_type == "text":
        return False

    media = msg.get(msg_type, {})
    media_id = media.get("id")
    caption = media.get("caption", "")
    mime = media.get("mime_type", "")
    ext = guess_extension_from_type(mime)

    media_url = get_media_url(media_id)
    if not media_url:
        add_message_to_history(sender_id, "user", f"[{msg_type.upper()}] (could not get URL)")
        return True

    path = download_media(media_url, media_id, ext)
    if not path:
        add_message_to_history(sender_id, "user", f"[{msg_type.upper()}] (download failed)")
        return True

    insert_media_record(media_id, sender_id, msg_type, caption, mime, path)
    note = f"[{msg_type.upper()}] {caption or mime}\nSaved at: {path}"
    add_message_to_history(sender_id, "user", note)
    log.info("Media saved: %s", path)
    return True
