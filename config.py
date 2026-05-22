"""Backward-compatible config surface. Prefer kai.settings.get_settings() for new code."""

from __future__ import annotations

from typing import Any

from kai.settings.loader import (
    BASE_DIR,
    Settings,
    _manifest_rag_source,
    get_settings,
    load_settings,
    reload_settings as _reload_settings_impl,
)

_EXPORT_NAMES: frozenset[str] = frozenset({
    "PORT", "TZ_REGION", "OFFICE_START", "OFFICE_END",
    "DEEPSEEK_API_KEY", "DEEPSEEK_BASE_URL", "DEEPSEEK_MODEL",
    "KAI_LLM_PROVIDER", "KAI_LLM_MODEL", "KAI_LLM_BASE_URL", "KAI_LLM_API_KEY",
    "KAI_QDRANT_ENABLED", "KAI_QDRANT_URL", "KAI_QDRANT_COLLECTION", "KAI_RERANKER_BACKEND",
    "KAI_GUARDRAILS_ENABLED",
    "KAI_CHATWOOT_API_BASE", "KAI_CHATWOOT_API_TOKEN", "KAI_CHATWOOT_ACCOUNT_ID",
    "KAI_CHATWOOT_ENFORCE_LIVE_HANDOVER",
    "KAI_FAQ_LEARN_ENABLED", "KAI_FAQ_LEARN_ASYNC", "KAI_FAQ_LEARN_FETCH_CHATWOOT",
    "KAI_FAQ_LEARN_MASTER_FAQ_MAX_CHARS", "KAI_FAQ_LEARN_USE_QUEUE",
    "KAI_FAQ_LEARN_LEGACY_APPEND", "KAI_FAQ_LEARN_ON_HANDOVER",
    "KAI_SOP_WRITEBACK_ENABLED", "KAI_SOP_MERGE_SYNC_ENABLED",
    "KAI_SOP_MERGE_SYNC_HOUR", "KAI_SOP_MERGE_SYNC_MINUTE",
    "GOOGLE_DOCS_SOP_DOC_ID",
    "TECH_BACKLOG_SHEET_ID", "TECH_BACKLOG_TAB_NAME", "TECH_ACTIVE_TAB_NAME",
    "GITHUB_REPO", "GITHUB_BRANCH", "BUKAPILOT_REPO", "BUKAPILOT_BRANCH",
    "CS_RECIPIENTS", "AGENT_NUMBERS", "ADMIN_TOKEN",
    "SOP_DOC_URL", "WARRANTY_CSV_URL",
    "GOOGLE_SHEETS_WARRANTY_SHEET_ID", "GOOGLE_SHEETS_WARRANTY_GID", "GOOGLE_SHEETS_WARRANTY_EXTRA_GID",
    "SOP_SYNC_STATE_PATH", "AGENT_WORKSPACE", "MASTER_FAQ_PATH", "AGENT_LEARNT_FAQ_PATH",
    "FAQ_LEARN_QUEUE_DIR", "WORKSPACE_MANIFEST_PATH", "CONTEXT_REGISTRY_YAML",
    "BING_API_KEY", "VEHICLE_SUPPORT_OFFICIAL_URL", "VEHICLE_SUPPORT_HTTP_TIMEOUT_SECONDS",
    "VEHICLE_SUPPORT_MIN_EVIDENCE_SCORE",
    "KAI_ROUTE_AGENT_MAX_STEPS", "KAI_ROUTE_AGENT_DEBUG_ENABLED", "KAI_COMPILE_EXTRA_ARTIFACTS",
    "MIN_SUPPORTED_YEAR", "SESSION_IDLE_HOURS", "SESSION_MAX_HISTORY_MESSAGES", "MEMORY_DEPTH",
    "MEMORY_SUMMARY_MAX_CHARS", "MEMORY_TTL_PREFERENCES_DAYS",
    "MEMORY_TTL_DEVICE_ACCOUNT_DAYS", "MEMORY_TTL_TEMP_ISSUE_DAYS",
})

_BOOL_EXPORTS = frozenset({
    "KAI_QDRANT_ENABLED", "KAI_GUARDRAILS_ENABLED", "KAI_CHATWOOT_ENFORCE_LIVE_HANDOVER",
    "KAI_FAQ_LEARN_ENABLED", "KAI_FAQ_LEARN_ASYNC", "KAI_FAQ_LEARN_FETCH_CHATWOOT",
    "KAI_FAQ_LEARN_USE_QUEUE", "KAI_FAQ_LEARN_LEGACY_APPEND", "KAI_FAQ_LEARN_ON_HANDOVER",
    "KAI_SOP_WRITEBACK_ENABLED", "KAI_SOP_MERGE_SYNC_ENABLED",
    "KAI_ROUTE_AGENT_DEBUG_ENABLED", "KAI_COMPILE_EXTRA_ARTIFACTS",
})


def _export_value(name: str, s: Settings) -> Any:
    if name in _BOOL_EXPORTS:
        return "1" if getattr(s, name.lower()) else "0"
    if name == "KAI_FAQ_LEARN_MASTER_FAQ_MAX_CHARS":
        return s.kai_faq_learn_master_faq_max_chars
    if name == "KAI_SOP_MERGE_SYNC_HOUR":
        return s.kai_sop_merge_sync_hour
    if name == "KAI_SOP_MERGE_SYNC_MINUTE":
        return s.kai_sop_merge_sync_minute
    if name in {"GITHUB_REPO", "BUKAPILOT_REPO"}:
        return s.github_repo or s.bukapilot_repo
    if name in {"GITHUB_BRANCH", "BUKAPILOT_BRANCH"}:
        return s.github_branch or s.bukapilot_branch
    if name == "CS_RECIPIENTS":
        return list(s.cs_recipients)
    if name == "AGENT_NUMBERS":
        return set(s.agent_numbers)
    if name == "MASTER_FAQ_PATH":
        return str(s.resolve_master_faq_path())
    if name == "SOP_SYNC_STATE_PATH":
        return str(s.sop_sync_state_path)
    if name == "AGENT_WORKSPACE":
        return str(s.agent_workspace)
    if name == "AGENT_LEARNT_FAQ_PATH":
        return str(s.agent_learnt_faq_path)
    if name == "FAQ_LEARN_QUEUE_DIR":
        return str(s.faq_learn_queue_dir)
    if name == "WORKSPACE_MANIFEST_PATH":
        return str(s.workspace_manifest_path)
    if name == "CONTEXT_REGISTRY_YAML":
        return str(s.agent_workspace / "04_context" / "context_registry.yaml")
    return getattr(s, name.lower())


def reload_settings() -> Settings:
    """Reload Settings and drop cached config module exports (for unittest.mock.patch)."""
    s = _reload_settings_impl()
    for key in _EXPORT_NAMES:
        globals().pop(key, None)
    return s


def resolve_master_faq_path() -> str:
    return str(get_settings().resolve_master_faq_path())


def __getattr__(name: str) -> Any:
    if name in _EXPORT_NAMES:
        return _export_value(name, get_settings())
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "Settings",
    "_manifest_rag_source",
    "get_settings",
    "load_settings",
    "reload_settings",
    "resolve_master_faq_path",
    *sorted(_EXPORT_NAMES),
]
