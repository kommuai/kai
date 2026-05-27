from __future__ import annotations

"""Unified runtime knowledge refresh (admin API + scheduled job)."""

from typing import Any


def refresh_runtime_knowledge(*, compile_kb: bool = True) -> dict[str, Any]:
    from kai.content.channels import get_channel_config
    from kai.content.copy import get_chat_copy
    from kai.services.container import get_kai_service, get_support_runtime_service
    from kai.workspace.reload import reload_workspace_caches
    from kai.workspace.tools_config import needs_warranty_cache

    reload_workspace_caches()
    runtime_out = get_support_runtime_service().startup(
        compile_kb=compile_kb,
        warm_warranty=needs_warranty_cache(),
    )
    kai = get_kai_service()
    kai._copy = get_chat_copy()
    kai._channels = get_channel_config()
    return {"ok": True, "runtime_refresh": runtime_out}
