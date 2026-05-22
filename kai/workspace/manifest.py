from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from kai.settings import get_settings


@dataclass(frozen=True)
class WorkspacePaths:
    system_prompt: str = "01_core/system_prompt.md"
    knowledge_primary: str = "02_knowledge/faq/master_faq.md"
    knowledge_compiled_dir: str = "compiled"
    chat_copy: str = "05_copy/chat_copy.yaml"
    channels_handover: str = "04_channels/handover.yaml"
    settings: str = "settings.yaml"
    tools: str = "03_tools/tools.yaml"


@dataclass(frozen=True)
class WorkspaceKnowledge:
    format: str = "master_faq_v1"
    compile_artifact: str = "kb_chunks.jsonl"
    inject_mode: str = "full_context"
    faq_preamble: str = ""


@dataclass(frozen=True)
class WorkspaceManifest:
    version: str
    tenant_id: str
    display_name: str
    default_lang: str
    timezone: str
    paths: WorkspacePaths
    knowledge: WorkspaceKnowledge
    tools_enabled: tuple[str, ...] = ()
    raw: dict[str, Any] = field(default_factory=dict, repr=False)

    def resolve(self, relative: str) -> Path:
        return get_settings().agent_workspace / relative


def _manifest_yaml_path() -> Path:
    return get_settings().agent_workspace / "00_manifest.yaml"


def _manifest_md_path() -> Path:
    return get_settings().workspace_manifest_path


def _parse_md_frontmatter(path: Path) -> dict[str, Any]:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return {}
    if not raw.startswith("---"):
        return {}
    end = raw.find("\n---", 3)
    if end < 0:
        return {}
    block = raw[3:end].strip()
    try:
        data = yaml.safe_load(block) or {}
    except yaml.YAMLError:
        return {}
    return data if isinstance(data, dict) else {}


def _paths_from_dict(data: dict[str, Any]) -> WorkspacePaths:
    paths = data.get("paths") if isinstance(data.get("paths"), dict) else {}
    knowledge = data.get("knowledge") if isinstance(data.get("knowledge"), dict) else {}
    compiled = knowledge.get("compiled_dir") or paths.get("compiled_dir") or "compiled"
    return WorkspacePaths(
        system_prompt=str(paths.get("system_prompt") or data.get("system_prompt") or "01_core/system_prompt.md"),
        knowledge_primary=str(
            paths.get("knowledge_primary")
            or paths.get("primary")
            or data.get("rag_source")
            or "02_knowledge/faq/master_faq.md"
        ),
        knowledge_compiled_dir=str(compiled),
        chat_copy=str(paths.get("chat_copy") or data.get("chat_copy") or "05_copy/chat_copy.yaml"),
        channels_handover=str(paths.get("channels_handover") or "04_channels/handover.yaml"),
        settings=str(paths.get("settings") or data.get("settings_defaults") or "settings.yaml"),
        tools=str(paths.get("tools") or "03_tools/tools.yaml"),
    )


def _knowledge_from_dict(data: dict[str, Any]) -> WorkspaceKnowledge:
    knowledge = data.get("knowledge") if isinstance(data.get("knowledge"), dict) else {}
    compile_name = knowledge.get("compile")
    if isinstance(compile_name, str) and compile_name.endswith(".jsonl"):
        artifact = compile_name
    else:
        artifact = "kb_chunks.jsonl"
    return WorkspaceKnowledge(
        format=str(knowledge.get("format") or "master_faq_v1"),
        compile_artifact=artifact,
        inject_mode=str(knowledge.get("inject_mode") or "retrieval_first"),
        faq_preamble=str(knowledge.get("faq_preamble") or "").strip(),
    )


def _tenant_from_dict(data: dict[str, Any]) -> tuple[str, str, str, str]:
    tenant = data.get("tenant") if isinstance(data.get("tenant"), dict) else {}
    return (
        str(tenant.get("id") or data.get("tenant_id") or "default"),
        str(tenant.get("display_name") or data.get("agent_name") or "Support Bot"),
        str(tenant.get("default_lang") or "en"),
        str(tenant.get("timezone") or "Asia/Kuala_Lumpur"),
    )


def _tools_enabled_from_dict(data: dict[str, Any]) -> tuple[str, ...]:
    tools = data.get("tools")
    if isinstance(tools, dict):
        enabled = tools.get("enabled")
        if isinstance(enabled, list):
            return tuple(str(x).strip() for x in enabled if str(x).strip())
    return ()


def manifest_from_dict(data: dict[str, Any]) -> WorkspaceManifest:
    tenant_id, display_name, default_lang, timezone = _tenant_from_dict(data)
    enabled = _tools_enabled_from_dict(data)
    return WorkspaceManifest(
        version=str(data.get("version") or "1"),
        tenant_id=tenant_id,
        display_name=display_name,
        default_lang=default_lang,
        timezone=timezone,
        paths=_paths_from_dict(data),
        knowledge=_knowledge_from_dict(data),
        tools_enabled=enabled,
        raw=data,
    )


def load_workspace_manifest(*, force: bool = False) -> WorkspaceManifest:
    if force:
        reload_workspace_manifest()
    return _load_workspace_manifest_cached()


@lru_cache(maxsize=1)
def _load_workspace_manifest_cached() -> WorkspaceManifest:
    yaml_path = _manifest_yaml_path()
    if yaml_path.is_file():
        data = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
        if isinstance(data, dict):
            return manifest_from_dict(data)

    md_path = _manifest_md_path()
    if md_path.is_file():
        return manifest_from_dict(_parse_md_frontmatter(md_path))

    return manifest_from_dict({})


def reload_workspace_manifest() -> WorkspaceManifest:
    _load_workspace_manifest_cached.cache_clear()
    from kai.workspace.tools_config import reload_tools_config

    reload_tools_config()
    return load_workspace_manifest()
