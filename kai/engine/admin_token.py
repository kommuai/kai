from __future__ import annotations

import os

from kai.settings import get_settings

_WEAK_TOKENS = frozenset({"", "changeme-strong"})


def admin_token_is_weak() -> bool:
    token = (get_settings().admin_token or "").strip()
    return token in _WEAK_TOKENS


def require_strong_admin_token_enabled() -> bool:
    if os.getenv("KAI_REQUIRE_STRONG_ADMIN_TOKEN", "").strip().lower() in {"1", "true", "yes", "on"}:
        return True
    return os.getenv("KAI_STRICT_STARTUP", "").strip().lower() in {"1", "true", "yes", "on"}


def assert_admin_token_acceptable_for_boot() -> None:
    if require_strong_admin_token_enabled() and admin_token_is_weak():
        raise RuntimeError(
            "ADMIN_TOKEN is missing or weak; set a long random token or disable KAI_STRICT_STARTUP / "
            "KAI_REQUIRE_STRONG_ADMIN_TOKEN"
        )
