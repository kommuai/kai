from enum import Enum

from kai.settings import get_settings


class RouteMode(str, Enum):
    HYBRID = "hybrid"
    AGENT_FIRST = "agent_first"


def get_route_mode() -> RouteMode:
    raw = get_settings().kai_route_mode.strip().lower()
    # Backward compat: map removed stable_only to hybrid
    if raw == "stable_only":
        return RouteMode.HYBRID
    if raw in {m.value for m in RouteMode}:
        return RouteMode(raw)
    return RouteMode.HYBRID

