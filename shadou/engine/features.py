from __future__ import annotations

from dataclasses import dataclass

from shadou.settings import get_settings


@dataclass(frozen=True)
class WorkspaceFeatures:
    """What this workspace needs from the engine (deps, startup, schedulers)."""

    enabled_builtins: tuple[str, ...]
    warranty_cache: bool
    sheet_backlog: bool
    plugin_ids: tuple[str, ...]
    qdrant_retrieval: bool
    optional_pip_hint: str


def sop_merge_scheduler_enabled() -> bool:
    from shadou.settings import get_settings
    from shadou.workspace.manifest import load_workspace_manifest

    if not get_settings().shadou_sop_merge_sync_enabled:
        return False
    raw = load_workspace_manifest().raw.get("sop_sync")
    if isinstance(raw, dict) and raw.get("enabled") is False:
        return False
    return True


def get_workspace_features() -> WorkspaceFeatures:
    from shadou.workspace.tools_config import (
        enabled_canonical_builtins,
        load_tools_config,
        needs_github_tools,
        needs_sheet_backlog,
        needs_warranty_cache,
    )

    builtins = tuple(sorted(enabled_canonical_builtins()))
    plugins = tuple(sorted({e.plugin for e in load_tools_config().enabled_entries() if e.plugin}))
    s = get_settings()

    hints: list[str] = []
    if needs_warranty_cache() or needs_sheet_backlog():
        hints.append("google-api")
    if needs_github_tools():
        hints.append("SHADOU_GITHUB_REPO")
    if plugins:
        hints.append("plugins+ddddocr")
    if s.shadou_qdrant_enabled:
        hints.append("qdrant-client")

    return WorkspaceFeatures(
        enabled_builtins=builtins,
        warranty_cache=needs_warranty_cache(),
        sheet_backlog=needs_sheet_backlog(),
        plugin_ids=plugins,
        qdrant_retrieval=bool(s.shadou_qdrant_enabled),
        optional_pip_hint=", ".join(hints) if hints else "",
    )
