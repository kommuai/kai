import os
from enum import Enum


class RouteMode(str, Enum):
    HYBRID = "hybrid"
    AGENT_FIRST = "agent_first"


def get_route_mode() -> RouteMode:
    raw = os.getenv("KAI_ROUTE_MODE", RouteMode.HYBRID.value).strip().lower()
    # Backward compat: map removed stable_only to hybrid
    if raw == "stable_only":
        return RouteMode.HYBRID
    if raw in {m.value for m in RouteMode}:
        return RouteMode(raw)
    return RouteMode.HYBRID


def get_default_timeout_ms() -> int:
    return int(os.getenv("KAI_TOOL_TIMEOUT_MS", "8000"))


def get_default_retry_count() -> int:
    return int(os.getenv("KAI_TOOL_RETRY_COUNT", "1"))


def get_shadow_mode_enabled() -> bool:
    return os.getenv("KAI_SHADOW_MODE", "1").strip() in {"1", "true", "yes", "on"}

