"""Backward-compatible config surface. Prefer kai.settings.get_settings() for new code."""

from __future__ import annotations

from kai.settings.loader import (
    BASE_DIR,
    Settings,
    _manifest_rag_source,
    get_settings,
    load_settings,
    reload_settings,
)

_s = get_settings()

# App / time
PORT = _s.port
TZ_REGION = _s.tz_region
OFFICE_START = _s.office_start
OFFICE_END = _s.office_end

# LLM
DEEPSEEK_API_KEY = _s.deepseek_api_key
DEEPSEEK_BASE_URL = _s.deepseek_base_url
DEEPSEEK_MODEL = _s.deepseek_model
KAI_LLM_PROVIDER = _s.kai_llm_provider
KAI_LLM_MODEL = _s.kai_llm_model
KAI_LLM_BASE_URL = _s.kai_llm_base_url
KAI_LLM_API_KEY = _s.kai_llm_api_key

# Retrieval
KAI_QDRANT_ENABLED = "1" if _s.kai_qdrant_enabled else "0"
KAI_QDRANT_URL = _s.kai_qdrant_url
KAI_QDRANT_COLLECTION = _s.kai_qdrant_collection
KAI_RERANKER_BACKEND = _s.kai_reranker_backend
KAI_GUARDRAILS_ENABLED = "1" if _s.kai_guardrails_enabled else "0"

# Chatwoot
KAI_CHATWOOT_API_BASE = _s.kai_chatwoot_api_base
KAI_CHATWOOT_API_TOKEN = _s.kai_chatwoot_api_token
KAI_CHATWOOT_ACCOUNT_ID = _s.kai_chatwoot_account_id
KAI_CHATWOOT_ENFORCE_LIVE_HANDOVER = "1" if _s.kai_chatwoot_enforce_live_handover else "0"

# FAQ learn
KAI_FAQ_LEARN_ENABLED = "1" if _s.kai_faq_learn_enabled else "0"
KAI_FAQ_LEARN_ASYNC = "1" if _s.kai_faq_learn_async else "0"
KAI_FAQ_LEARN_FETCH_CHATWOOT = "1" if _s.kai_faq_learn_fetch_chatwoot else "0"
KAI_FAQ_LEARN_MASTER_FAQ_MAX_CHARS = _s.kai_faq_learn_master_faq_max_chars
KAI_FAQ_LEARN_USE_QUEUE = "1" if _s.kai_faq_learn_use_queue else "0"
KAI_FAQ_LEARN_LEGACY_APPEND = "1" if _s.kai_faq_learn_legacy_append else "0"
KAI_FAQ_LEARN_ON_HANDOVER = "1" if _s.kai_faq_learn_on_handover else "0"

# SOP
KAI_SOP_WRITEBACK_ENABLED = "1" if _s.kai_sop_writeback_enabled else "0"
KAI_SOP_MERGE_SYNC_ENABLED = "1" if _s.kai_sop_merge_sync_enabled else "0"
KAI_SOP_MERGE_SYNC_HOUR = _s.kai_sop_merge_sync_hour
KAI_SOP_MERGE_SYNC_MINUTE = _s.kai_sop_merge_sync_minute
GOOGLE_DOCS_SOP_DOC_ID = _s.google_docs_sop_doc_id

# Sheets
TECH_BACKLOG_SHEET_ID = _s.tech_backlog_sheet_id
TECH_BACKLOG_TAB_NAME = _s.tech_backlog_tab_name
TECH_ACTIVE_TAB_NAME = _s.tech_active_tab_name
GITHUB_REPO = _s.github_repo or _s.bukapilot_repo
GITHUB_BRANCH = _s.github_branch or _s.bukapilot_branch
BUKAPILOT_REPO = GITHUB_REPO
BUKAPILOT_BRANCH = GITHUB_BRANCH

CS_RECIPIENTS = list(_s.cs_recipients)
AGENT_NUMBERS = set(_s.agent_numbers)
ADMIN_TOKEN = _s.admin_token

SOP_DOC_URL = _s.sop_doc_url
WARRANTY_CSV_URL = _s.warranty_csv_url
GOOGLE_SHEETS_WARRANTY_SHEET_ID = _s.google_sheets_warranty_sheet_id
GOOGLE_SHEETS_WARRANTY_GID = _s.google_sheets_warranty_gid
GOOGLE_SHEETS_WARRANTY_EXTRA_GID = _s.google_sheets_warranty_extra_gid

SOP_SYNC_STATE_PATH = str(_s.sop_sync_state_path)
AGENT_WORKSPACE = str(_s.agent_workspace)
MASTER_FAQ_PATH = str(_s.master_faq_path)
AGENT_LEARNT_FAQ_PATH = str(_s.agent_learnt_faq_path)
FAQ_LEARN_QUEUE_DIR = str(_s.faq_learn_queue_dir)
WORKSPACE_MANIFEST_PATH = str(_s.workspace_manifest_path)
# tools/new_context.py
CONTEXT_REGISTRY_YAML = str(_s.agent_workspace / "04_context" / "context_registry.yaml")

BING_API_KEY = _s.bing_api_key
VEHICLE_SUPPORT_OFFICIAL_URL = _s.vehicle_support_official_url
VEHICLE_SUPPORT_HTTP_TIMEOUT_SECONDS = _s.vehicle_support_http_timeout_seconds
VEHICLE_SUPPORT_MIN_EVIDENCE_SCORE = _s.vehicle_support_min_evidence_score

KAI_ROUTE_AGENT_MAX_STEPS = _s.kai_route_agent_max_steps
KAI_ROUTE_AGENT_DEBUG_ENABLED = "1" if _s.kai_route_agent_debug_enabled else "0"
KAI_COMPILE_EXTRA_ARTIFACTS = "1" if _s.kai_compile_extra_artifacts else "0"

MIN_SUPPORTED_YEAR = _s.min_supported_year
SESSION_IDLE_HOURS = _s.session_idle_hours
SESSION_MAX_HISTORY_MESSAGES = _s.session_max_history_messages
MEMORY_DEPTH = _s.session_max_history_messages
MEMORY_SUMMARY_MAX_CHARS = _s.memory_summary_max_chars
MEMORY_TTL_PREFERENCES_DAYS = _s.memory_ttl_preferences_days
MEMORY_TTL_DEVICE_ACCOUNT_DAYS = _s.memory_ttl_device_account_days
MEMORY_TTL_TEMP_ISSUE_DAYS = _s.memory_ttl_temp_issue_days


def resolve_master_faq_path() -> str:
    return str(_s.resolve_master_faq_path())


__all__ = [
    "Settings",
    "_manifest_rag_source",
    "get_settings",
    "load_settings",
    "reload_settings",
    "resolve_master_faq_path",
]
