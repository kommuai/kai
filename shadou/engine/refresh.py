from __future__ import annotations

"""Unified runtime knowledge refresh (admin API + scheduled job)."""

from typing import Any


def refresh_runtime_knowledge(*, compile_kb: bool = True) -> dict[str, Any]:
    from shadou.content.channels import get_channel_config
    from shadou.content.copy import get_chat_copy
    from shadou.services.container import get_shadou_service, get_support_runtime_service
    from shadou.workspace.reload import reload_workspace_caches
    from shadou.workspace.tools_config import needs_warranty_cache

    reload_workspace_caches()
    runtime_out = get_support_runtime_service().startup(
        compile_kb=compile_kb,
        warm_warranty=needs_warranty_cache(),
    )
    svc = get_shadou_service()
    svc._copy = get_chat_copy()
    svc._channels = get_channel_config()
    return {"ok": True, "runtime_refresh": runtime_out}
