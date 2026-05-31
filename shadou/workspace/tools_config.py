from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from shadou.support_runtime.tools.catalog import resolve_builtin_id
from shadou.settings import get_settings
from shadou.workspace.manifest import load_workspace_data, load_workspace_manifest, workspace_yaml_path


@dataclass(frozen=True)
class ToolConfigEntry:
    id: str
    builtin: str
    enabled: bool = True
    description: str = ""
    plugin: str = ""
    params: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ToolsConfig:
    path: Path
    entries: tuple[ToolConfigEntry, ...]
    raw: dict[str, Any] = field(default_factory=dict, repr=False)

    def enabled_entries(self) -> list[ToolConfigEntry]:
        return [e for e in self.entries if e.enabled]


def _tools_config_path() -> Path:
    return workspace_yaml_path()


def _tools_raw_dict() -> dict[str, Any]:
    data = load_workspace_data()
    for key in ("tools_profile", "tools"):
        block = data.get(key)
        if isinstance(block, dict) and (
            "active_profile" in block or "profiles" in block or "tools" in block or "profile_overrides" in block
        ):
            return block
    return {}


def _parse_tools_list(data: list[Any]) -> list[ToolConfigEntry]:
    out: list[ToolConfigEntry] = []
    for item in data:
        if isinstance(item, str):
            name = item.strip()
            if name:
                out.append(ToolConfigEntry(id=name, builtin=name, enabled=True))
            continue
        if not isinstance(item, dict):
            continue
        tool_id = str(item.get("id") or item.get("name") or "").strip()
        if not tool_id:
            continue
        builtin = resolve_builtin_id(str(item.get("builtin") or tool_id).strip())
        enabled = item.get("enabled", True)
        if isinstance(enabled, str):
            enabled = enabled.strip().lower() not in {"0", "false", "no", "off"}
        out.append(
            ToolConfigEntry(
                id=tool_id,
                builtin=builtin,
                enabled=bool(enabled),
                description=str(item.get("description") or "").strip(),
                plugin=str(item.get("plugin") or "").strip(),
                params=dict(item.get("params") or {}) if isinstance(item.get("params"), dict) else {},
            )
        )
    return out


def _profile_tool_ids(raw: dict[str, Any]) -> list[str]:
    profile = str(raw.get("active_profile") or raw.get("profile") or "").strip()
    profiles = raw.get("profiles")
    if not profile or not isinstance(profiles, dict):
        return []
    ids = profiles.get(profile)
    if isinstance(ids, list):
        return [str(x).strip() for x in ids if str(x).strip()]
    return []


@lru_cache(maxsize=1)
def load_tools_config() -> ToolsConfig:
    path = _tools_config_path()
    raw = _tools_raw_dict()
    if not raw:
        manifest = load_workspace_manifest()
        ids = list(manifest.tools_enabled) or _default_builtin_ids()
        entries = [ToolConfigEntry(id=i, builtin=i, enabled=True) for i in ids]
        return ToolsConfig(path=path, entries=tuple(entries), raw={})

    tools_list = raw.get("tools")
    if not isinstance(tools_list, list):
        tools_list = []

    if not tools_list:
        profile_ids = _profile_tool_ids(raw)
        overrides = raw.get("profile_overrides") if isinstance(raw.get("profile_overrides"), dict) else {}
        if profile_ids:
            tools_list = []
            for i in profile_ids:
                canonical = resolve_builtin_id(i)
                item: dict[str, Any] = {"id": i, "builtin": canonical, "enabled": True}
                ov = overrides.get(i) or overrides.get(canonical)
                if isinstance(ov, dict):
                    item.update(ov)
                tools_list.append(item)

    entries = _parse_tools_list(tools_list)
    if not entries:
        entries = [ToolConfigEntry(id=i, builtin=i, enabled=True) for i in _default_builtin_ids()]
    return ToolsConfig(path=path, entries=tuple(entries), raw=raw)


def reload_tools_config() -> ToolsConfig:
    load_tools_config.cache_clear()
    load_workspace_data.cache_clear()
    return load_tools_config()


def _default_builtin_ids() -> list[str]:
    from shadou.support_runtime.tools.catalog import default_tool_ids

    return default_tool_ids()


def enabled_canonical_builtins() -> set[str]:
    return {resolve_builtin_id(e.builtin) for e in load_tools_config().enabled_entries() if not e.plugin}


def needs_warranty_cache() -> bool:
    return "lookup_sheet_record" in enabled_canonical_builtins()


def needs_sheet_backlog() -> bool:
    ids = enabled_canonical_builtins()
    return bool(ids.intersection({"lookup_sheet_backlog", "log_sheet_backlog", "lookup_backlog", "log_backlog"}))


def needs_github_tools() -> bool:
    ids = enabled_canonical_builtins()
    return bool(ids.intersection({"search_github_repo", "read_github_file"}))
