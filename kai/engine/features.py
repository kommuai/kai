from __future__ import annotations

from dataclasses import dataclass

from kai.settings import get_settings


@dataclass(frozen=True)
class WorkspaceFeatures:
    """What this workspace needs from the engine (deps, startup, schedulers)."""

    enabled_builtins: tuple[str, ...]
    warranty_cache: bool
    sheet_backlog: bool
    plugin_ids: tuple[str, ...]
    qdrant_retrieval: bool
    optional_pip_hint: str


def get_workspace_features() -> WorkspaceFeatures:
    from kai.workspace.tools_config import (
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
        hints.append("KAI_GITHUB_REPO")
    if plugins:
        hints.append("plugins+ddddocr")
    if s.kai_qdrant_enabled:
        hints.append("qdrant-client")

    return WorkspaceFeatures(
        enabled_builtins=builtins,
        warranty_cache=needs_warranty_cache(),
        sheet_backlog=needs_sheet_backlog(),
        plugin_ids=plugins,
        qdrant_retrieval=bool(s.kai_qdrant_enabled),
        optional_pip_hint=", ".join(hints) if hints else "",
    )
