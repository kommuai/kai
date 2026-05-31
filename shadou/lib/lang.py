"""Resolve reply language (EN/BM) from workspace default or session — no auto-detection."""

from __future__ import annotations

from shadou.lib.session_state import get_session


def resolve_lang(*, user_id: str = "", explicit: str | None = None) -> str:
    """EN or BM for copy/footers. explicit > session.lang > workspace tenant.default_lang."""
    if explicit:
        code = explicit.strip().upper()
        if code in ("BM", "MS", "MALAY"):
            return "BM"
        return "EN"
    if user_id:
        stored = (get_session(user_id).get("lang") or "").strip().upper()
        if stored in ("EN", "BM"):
            return stored
    try:
        from shadou.workspace.manifest import load_workspace_manifest

        raw = (load_workspace_manifest().default_lang or "en").strip().lower()
        if raw in ("bm", "ms", "malay"):
            return "BM"
    except Exception:  # noqa: BLE001
        pass
    return "EN"
