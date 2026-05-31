from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from shadou.settings import get_settings


def workspace_root() -> Path:
    return get_settings().shadou_home


def resolve_workspace_path(*parts: str) -> Path:
    return workspace_root().joinpath(*parts)


def manifest_relative_path(key: str, default: str) -> str:
    """Resolve a path key from workspace.yaml (system_prompt, knowledge_primary, …)."""
    from shadou.workspace.manifest import load_workspace_manifest

    manifest = load_workspace_manifest()
    mapping = {
        "system_prompt": manifest.paths.system_prompt,
        "knowledge_primary": manifest.paths.knowledge_primary,
    }
    return mapping.get(key, default)


@lru_cache(maxsize=8)
def read_text_file(relative_path: str) -> str:
    path = resolve_workspace_path(*relative_path.split("/"))
    if path.is_file():
        return path.read_text(encoding="utf-8")
    return ""
