from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parents[2]


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default)


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


def _env_bool(name: str, default: str = "0") -> bool:
    return _env(name, default).strip().lower() in {"1", "true", "yes", "on"}


def _split_list(name: str, default: str = "") -> list[str]:
    return [s.strip() for s in _env(name, default).split(",") if s.strip()]


def _manifest_rag_source(manifest_path: str | Path) -> str:
    try:
        raw = Path(manifest_path).read_text(encoding="utf-8")
    except OSError:
        return ""
    m = re.search(r"(?m)^\s*rag_source\s*:\s*([^\n#]+?)\s*$", raw)
    if not m:
        return ""
    return m.group(1).strip().strip('"').strip("'")


@dataclass(frozen=True)
class Settings:
    # App / time
    port: int = 8000
    tz_region: str = "Asia/Kuala_Lumpur"
    office_start: int = 10
    office_end: int = 18

    # LLM
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    deepseek_model: str = "deepseek-chat"
    kai_llm_provider: str = "deepseek"
    kai_llm_model: str = ""
    kai_llm_base_url: str = ""
    kai_llm_api_key: str = ""
    kai_embed_model: str = "text-embedding-3-small"

    # Retrieval
    kai_qdrant_enabled: bool = False
    kai_qdrant_url: str = "http://127.0.0.1:6333"
    kai_qdrant_api_key: str = ""
    kai_qdrant_collection: str = "kai_support"
    kai_reranker_backend: str = "provider"
    kai_guardrails_enabled: bool = False

    # Chatwoot
    kai_chatwoot_api_base: str = ""
    kai_chatwoot_api_token: str = ""
    kai_chatwoot_account_id: str = ""
    kai_chatwoot_enforce_live_handover: bool = False

    # FAQ learn
    kai_faq_learn_enabled: bool = True
    kai_faq_learn_async: bool = True
    kai_faq_learn_fetch_chatwoot: bool = True
    kai_faq_learn_master_faq_max_chars: int = 120000
    kai_faq_learn_use_queue: bool = True
    kai_faq_learn_legacy_append: bool = False
    kai_faq_learn_on_handover: bool = False

    # SOP
    kai_sop_writeback_enabled: bool = False
    kai_sop_merge_sync_enabled: bool = False
    kai_sop_merge_sync_hour: int = 8
    kai_sop_merge_sync_minute: int = 0
    google_docs_sop_doc_id: str = ""
    sop_doc_url: str = ""

    # Sheets / backlog
    tech_backlog_sheet_id: str = ""
    tech_backlog_tab_name: str = "Chatbot Backlog"
    tech_active_tab_name: str = "Active"
    github_repo: str = ""
    github_branch: str = "main"
    bukapilot_repo: str = ""  # deprecated alias; use github_repo
    bukapilot_branch: str = "main"
    google_sheets_credentials_json: str = ""
    warranty_csv_url: str = ""
    extra_warranty_csv_url: str = ""
    google_sheets_warranty_sheet_id: str = ""
    google_sheets_warranty_gid: str = ""
    google_sheets_warranty_extra_gid: str = ""

    # Admin / lists
    admin_token: str = "changeme-strong"
    cs_recipients: list[str] = field(default_factory=list)
    agent_numbers: frozenset[str] = field(default_factory=frozenset)

    # Paths
    base_dir: Path = field(default_factory=lambda: BASE_DIR)
    agent_workspace: Path = field(default_factory=lambda: BASE_DIR / "agent_workspace")
    master_faq_path: Path = field(default_factory=lambda: BASE_DIR / "agent_workspace" / "02_knowledge" / "faq" / "master_faq.md")
    agent_learnt_faq_path: Path = field(default_factory=lambda: BASE_DIR / "agent_workspace" / "02_knowledge" / "faq" / "agent_learnt_faq.md")
    faq_learn_queue_dir: Path = field(default_factory=lambda: BASE_DIR / "agent_workspace" / "02_knowledge" / "faq" / "learn_queue")
    workspace_manifest_path: Path = field(default_factory=lambda: BASE_DIR / "agent_workspace" / "00_manifest.yaml")
    sop_sync_state_path: Path = field(default_factory=lambda: BASE_DIR / "data" / "sop" / "sop_sync_state.json")
    session_db_path: str = "data/sessions.db"

    # Vehicle / search
    bing_api_key: str = ""
    vehicle_support_official_url: str = ""
    vehicle_support_http_timeout_seconds: int = 8
    vehicle_support_min_evidence_score: float = 0.65

    # Agent routing
    kai_route_mode: str = "hybrid"
    kai_route_agent_max_steps: int = 8
    kai_route_agent_debug_enabled: bool = False
    kai_compile_extra_artifacts: bool = False

    # Session
    session_idle_hours: int = 24
    session_max_history_messages: int = 100
    memory_summary_max_chars: int = 1200
    memory_ttl_preferences_days: int = 365
    memory_ttl_device_account_days: int = 90
    memory_ttl_temp_issue_days: int = 7
    min_supported_year: int = 2016

    # Integrations
    kai_github_token: str = ""
    kai_service_keys_raw: str = ""
    meta_permanent_token: str = ""
    smartserva_username: str = ""
    smartserva_password: str = ""

    def resolve_master_faq_path(self) -> Path:
        explicit = _env("MASTER_FAQ_PATH", "").strip()
        if explicit:
            p = Path(explicit)
            return p if p.is_absolute() else self.base_dir / p
        try:
            from kai.workspace.manifest import load_workspace_manifest

            manifest = load_workspace_manifest()
            candidate = self.agent_workspace / manifest.paths.knowledge_primary
            if candidate.is_file():
                return candidate
        except Exception:  # noqa: BLE001
            pass
        rag_rel = _manifest_rag_source(self.workspace_manifest_path)
        if rag_rel:
            candidate = self.agent_workspace / rag_rel
            if candidate.is_file():
                return candidate
        yaml_manifest = self.agent_workspace / "00_manifest.yaml"
        if yaml_manifest.is_file():
            rag_rel = _manifest_rag_source(yaml_manifest)
            if rag_rel:
                candidate = self.agent_workspace / rag_rel
                if candidate.is_file():
                    return candidate
        return self.master_faq_path


def load_settings() -> Settings:
    base = BASE_DIR
    deepseek_base = _env("DEEPSEEK_BASE_URL") or _env("DEEPSEEK_API_BASE", "https://api.deepseek.com/v1")
    deepseek_model = _env("DEEPSEEK_MODEL", "deepseek-chat")
    agent_ws = _env("AGENT_WORKSPACE", "agent_workspace")
    agent_workspace = Path(agent_ws) if Path(agent_ws).is_absolute() else base / agent_ws

    master_explicit = _env("MASTER_FAQ_PATH", "").strip()
    master_faq = (
        Path(master_explicit)
        if master_explicit
        else agent_workspace / "02_knowledge" / "faq" / "master_faq.md"
    )
    if master_explicit and not master_faq.is_absolute():
        master_faq = base / master_faq

    learnt = _env("AGENT_LEARNT_FAQ_PATH", "").strip()
    agent_learnt = (
        Path(learnt) if learnt else agent_workspace / "02_knowledge" / "faq" / "agent_learnt_faq.md"
    )
    if learnt and not agent_learnt.is_absolute():
        agent_learnt = base / agent_learnt

    queue = _env("FAQ_LEARN_QUEUE_DIR", "").strip()
    learn_queue = Path(queue) if queue else agent_workspace / "02_knowledge" / "faq" / "learn_queue"
    if queue and not learn_queue.is_absolute():
        learn_queue = base / learn_queue

    return Settings(
        port=_env_int("PORT", 8000),
        tz_region=_env("TZ_REGION", "Asia/Kuala_Lumpur"),
        office_start=_env_int("OFFICE_START", 10),
        office_end=_env_int("OFFICE_END", 18),
        deepseek_api_key=_env("DEEPSEEK_API_KEY"),
        deepseek_base_url=deepseek_base,
        deepseek_model=deepseek_model,
        kai_llm_provider=_env("KAI_LLM_PROVIDER", "deepseek"),
        kai_llm_model=_env("KAI_LLM_MODEL", deepseek_model),
        kai_llm_base_url=_env("KAI_LLM_BASE_URL", deepseek_base),
        kai_llm_api_key=_env("KAI_LLM_API_KEY", _env("DEEPSEEK_API_KEY")),
        kai_embed_model=_env("KAI_EMBED_MODEL", "text-embedding-3-small"),
        kai_qdrant_enabled=_env_bool("KAI_QDRANT_ENABLED"),
        kai_qdrant_url=_env("KAI_QDRANT_URL", "http://127.0.0.1:6333"),
        kai_qdrant_api_key=_env("KAI_QDRANT_API_KEY"),
        kai_qdrant_collection=_env("KAI_QDRANT_COLLECTION", "kai_support"),
        kai_reranker_backend=_env("KAI_RERANKER_BACKEND", "provider"),
        kai_guardrails_enabled=_env_bool("KAI_GUARDRAILS_ENABLED"),
        kai_chatwoot_api_base=_env("KAI_CHATWOOT_API_BASE"),
        kai_chatwoot_api_token=_env("KAI_CHATWOOT_API_TOKEN"),
        kai_chatwoot_account_id=_env("KAI_CHATWOOT_ACCOUNT_ID"),
        kai_chatwoot_enforce_live_handover=_env_bool("KAI_CHATWOOT_ENFORCE_LIVE_HANDOVER"),
        kai_faq_learn_enabled=_env_bool("KAI_FAQ_LEARN_ENABLED", "1"),
        kai_faq_learn_async=_env_bool("KAI_FAQ_LEARN_ASYNC", "1"),
        kai_faq_learn_fetch_chatwoot=_env_bool("KAI_FAQ_LEARN_FETCH_CHATWOOT", "1"),
        kai_faq_learn_master_faq_max_chars=_env_int("KAI_FAQ_LEARN_MASTER_FAQ_MAX_CHARS", 120000),
        kai_faq_learn_use_queue=_env_bool("KAI_FAQ_LEARN_USE_QUEUE", "1"),
        kai_faq_learn_legacy_append=_env_bool("KAI_FAQ_LEARN_LEGACY_APPEND"),
        kai_faq_learn_on_handover=_env_bool("KAI_FAQ_LEARN_ON_HANDOVER"),
        kai_sop_writeback_enabled=_env_bool("KAI_SOP_WRITEBACK_ENABLED"),
        kai_sop_merge_sync_enabled=_env_bool("KAI_SOP_MERGE_SYNC_ENABLED"),
        kai_sop_merge_sync_hour=_env_int("KAI_SOP_MERGE_SYNC_HOUR", 8),
        kai_sop_merge_sync_minute=_env_int("KAI_SOP_MERGE_SYNC_MINUTE", 0),
        google_docs_sop_doc_id=_env("GOOGLE_DOCS_SOP_DOC_ID"),
        sop_doc_url=_env("SOP_DOC_URL"),
        tech_backlog_sheet_id=_env("TECH_BACKLOG_SHEET_ID"),
        tech_backlog_tab_name=_env("TECH_BACKLOG_TAB_NAME", "Chatbot Backlog"),
        tech_active_tab_name=_env("TECH_ACTIVE_TAB_NAME", "Active"),
        github_repo=_env("KAI_GITHUB_REPO") or _env("BUKAPILOT_REPO"),
        github_branch=_env("KAI_GITHUB_BRANCH") or _env("BUKAPILOT_BRANCH", "main"),
        bukapilot_repo=_env("KAI_GITHUB_REPO") or _env("BUKAPILOT_REPO"),
        bukapilot_branch=_env("KAI_GITHUB_BRANCH") or _env("BUKAPILOT_BRANCH", "main"),
        google_sheets_credentials_json=_env("GOOGLE_SHEETS_CREDENTIALS_JSON"),
        warranty_csv_url=_env("WARRANTY_CSV_URL"),
        extra_warranty_csv_url=_env("EXTRA_WARRANTY_CSV_URL"),
        google_sheets_warranty_sheet_id=_env("GOOGLE_SHEETS_WARRANTY_SHEET_ID"),
        google_sheets_warranty_gid=_env("GOOGLE_SHEETS_WARRANTY_GID"),
        google_sheets_warranty_extra_gid=_env("GOOGLE_SHEETS_WARRANTY_EXTRA_GID"),
        admin_token=_env("ADMIN_TOKEN", "changeme-strong"),
        cs_recipients=_split_list("CS_RECIPIENTS"),
        agent_numbers=frozenset(_split_list("AGENT_NUMBERS")),
        base_dir=base,
        agent_workspace=agent_workspace,
        master_faq_path=master_faq,
        agent_learnt_faq_path=agent_learnt,
        faq_learn_queue_dir=learn_queue,
        workspace_manifest_path=agent_workspace / "00_manifest.yaml",
        sop_sync_state_path=base / "data" / "sop" / "sop_sync_state.json",
        session_db_path=_env("SESSION_DB_PATH", _env("DB_PATH", "data/sessions.db")),
        bing_api_key=_env("BING_API_KEY"),
        vehicle_support_official_url=_env("VEHICLE_SUPPORT_OFFICIAL_URL"),
        vehicle_support_http_timeout_seconds=_env_int("VEHICLE_SUPPORT_HTTP_TIMEOUT_SECONDS", 8),
        vehicle_support_min_evidence_score=_env_float("VEHICLE_SUPPORT_MIN_EVIDENCE_SCORE", 0.65),
        kai_route_mode=_env("KAI_ROUTE_MODE", "hybrid"),
        kai_route_agent_max_steps=_env_int("KAI_ROUTE_AGENT_MAX_STEPS", 8),
        kai_route_agent_debug_enabled=_env_bool("KAI_ROUTE_AGENT_DEBUG_ENABLED"),
        kai_compile_extra_artifacts=_env_bool("KAI_COMPILE_EXTRA_ARTIFACTS"),
        session_idle_hours=_env_int("SESSION_IDLE_HOURS", 24),
        session_max_history_messages=_env_int(
            "SESSION_MAX_HISTORY_MESSAGES",
            _env_int("MEMORY_DEPTH", 100),
        ),
        memory_summary_max_chars=_env_int("MEMORY_SUMMARY_MAX_CHARS", 1200),
        memory_ttl_preferences_days=_env_int("MEMORY_TTL_PREFERENCES_DAYS", 365),
        memory_ttl_device_account_days=_env_int("MEMORY_TTL_DEVICE_ACCOUNT_DAYS", 90),
        memory_ttl_temp_issue_days=_env_int("MEMORY_TTL_TEMP_ISSUE_DAYS", 7),
        kai_github_token=_env("KAI_GITHUB_TOKEN"),
        kai_service_keys_raw=_env("KAI_SERVICE_KEYS"),
        meta_permanent_token=_env("META_PERMANENT_TOKEN"),
        smartserva_username=_env("SMARTSERVA_USERNAME"),
        smartserva_password=_env("SMARTSERVA_PASSWORD"),
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return load_settings()


def reload_settings() -> Settings:
    get_settings.cache_clear()
    return get_settings()
