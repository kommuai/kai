from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from kai.content.copy import get_chat_copy
from kai.settings import get_settings
from kai.support_runtime.compiler import compile_canonical_knowledge
from kai.support_runtime.tools.catalog import builtin_catalog, resolve_builtin_id
from kai.workspace.manifest import load_workspace_manifest
from kai.workspace.tools_config import load_tools_config


@dataclass(frozen=True)
class ValidationIssue:
    level: str  # error | warn | ok
    code: str
    message: str


def validate_workspace(*, compile_kb: bool = True, ping_llm: bool = False) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    settings = get_settings()
    ws = settings.agent_workspace

    if not ws.is_dir():
        issues.append(ValidationIssue("error", "workspace_missing", f"Workspace not found: {ws}"))
        return issues

    manifest = load_workspace_manifest()
    yaml_manifest = ws / "00_manifest.yaml"
    if yaml_manifest.is_file():
        issues.append(ValidationIssue("ok", "manifest_yaml", f"Loaded manifest v{manifest.version} ({manifest.tenant_id})"))
    else:
        issues.append(
            ValidationIssue(
                "warn",
                "manifest_yaml_missing",
                "00_manifest.yaml not found; using 00_manifest.md frontmatter or defaults",
            )
        )

    for label, rel in (
        ("system_prompt", manifest.paths.system_prompt),
        ("knowledge", manifest.paths.knowledge_primary),
        ("chat_copy", manifest.paths.chat_copy),
        ("channels", manifest.paths.channels_handover),
        ("settings", manifest.paths.settings),
    ):
        path = manifest.resolve(rel)
        if path.is_file():
            issues.append(ValidationIssue("ok", f"path_{label}", str(path.relative_to(ws))))
        else:
            issues.append(ValidationIssue("error", f"path_{label}_missing", f"Missing {label}: {rel}"))

    tools_cfg = load_tools_config()
    if tools_cfg.path.is_file():
        issues.append(ValidationIssue("ok", "tools_yaml", f"{len(tools_cfg.enabled_entries())} tools enabled"))
    else:
        issues.append(ValidationIssue("warn", "tools_yaml_missing", f"Missing {manifest.paths.tools}; using defaults"))

    catalog = builtin_catalog()
    for entry in tools_cfg.enabled_entries():
        if entry.plugin:
            from kai.tools_plugins.runner import resolve_plugin_script

            if resolve_plugin_script(entry.plugin, entry.params):
                issues.append(ValidationIssue("ok", "plugin_script", f"Plugin {entry.plugin} script found"))
            else:
                issues.append(
                    ValidationIssue(
                        "error",
                        "plugin_script_missing",
                        f"Tool {entry.id} plugin={entry.plugin} has no script under 03_tools/plugins/",
                    )
                )
            continue
        canonical = resolve_builtin_id(entry.builtin)
        if entry.builtin and canonical not in catalog:
            issues.append(
                ValidationIssue("error", "unknown_builtin", f"Tool {entry.id} uses unknown builtin: {entry.builtin}")
            )

    try:
        get_chat_copy()
        issues.append(ValidationIssue("ok", "chat_copy_parse", "chat_copy.yaml parses"))
    except Exception as exc:  # noqa: BLE001
        issues.append(ValidationIssue("error", "chat_copy_parse", f"chat_copy.yaml failed: {exc}"))

    if compile_kb:
        try:
            counts = compile_canonical_knowledge()
            if counts.get("chunks", 0) > 0:
                issues.append(
                    ValidationIssue(
                        "ok",
                        "knowledge_compile",
                        f"Compiled {counts.get('chunks', 0)} chunks, {counts.get('intents', 0)} intents",
                    )
                )
            else:
                issues.append(ValidationIssue("error", "knowledge_compile", "FAQ compile produced zero chunks"))
        except Exception as exc:  # noqa: BLE001
            issues.append(ValidationIssue("error", "knowledge_compile", f"FAQ compile failed: {exc}"))

    if (settings.admin_token or "").strip() in {"", "changeme-strong"}:
        issues.append(
            ValidationIssue(
                "warn",
                "admin_token_weak",
                "Set a strong ADMIN_TOKEN in .env before production",
            )
        )

    api_key = (settings.kai_llm_api_key or settings.deepseek_api_key or "").strip()
    if not api_key:
        issues.append(ValidationIssue("warn", "llm_key_missing", "No LLM API key (KAI_LLM_API_KEY / DEEPSEEK_API_KEY)"))
    elif ping_llm:
        try:
            from kai.support_runtime.providers import build_provider

            provider = build_provider()
            out = provider.chat("Reply with exactly: OK", "Ping", max_tokens=8)
            if (out or "").strip():
                issues.append(ValidationIssue("ok", "llm_ping", "LLM provider responded"))
            else:
                issues.append(ValidationIssue("error", "llm_ping_empty", "LLM provider returned empty response"))
        except Exception as exc:  # noqa: BLE001
            issues.append(ValidationIssue("error", "llm_ping", f"LLM ping failed: {exc}"))

    chunks = manifest.resolve(manifest.paths.knowledge_compiled_dir) / manifest.knowledge.compile_artifact
    if chunks.is_file():
        issues.append(ValidationIssue("ok", "compiled_kb", str(chunks.relative_to(ws))))
    elif not compile_kb:
        issues.append(ValidationIssue("warn", "compiled_kb_missing", "Compiled kb not present (skipped compile)"))

    return issues


def workspace_is_healthy(issues: list[ValidationIssue]) -> bool:
    return not any(i.level == "error" for i in issues)


@lru_cache(maxsize=1)
def cached_readiness_issues() -> tuple[ValidationIssue, ...]:
    """Fast readiness probe (no FAQ compile, no LLM ping)."""
    return tuple(validate_workspace(compile_kb=False, ping_llm=False))


def invalidate_readiness_cache() -> None:
    cached_readiness_issues.cache_clear()
