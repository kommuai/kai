import os
from pathlib import Path
import re
from dotenv import load_dotenv
load_dotenv()

# App / time
PORT = int(os.getenv("PORT", 8000))
TZ_REGION = os.getenv("TZ_REGION", "Asia/Kuala_Lumpur")
OFFICE_START = int(os.getenv("OFFICE_START", 10))
OFFICE_END   = int(os.getenv("OFFICE_END", 18))

# LLM
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL") or os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com/v1")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
KAI_LLM_PROVIDER = os.getenv("KAI_LLM_PROVIDER", "deepseek")
KAI_LLM_MODEL = os.getenv("KAI_LLM_MODEL", DEEPSEEK_MODEL)
KAI_LLM_BASE_URL = os.getenv("KAI_LLM_BASE_URL", DEEPSEEK_BASE_URL)
KAI_LLM_API_KEY = os.getenv("KAI_LLM_API_KEY", DEEPSEEK_API_KEY)
KAI_QDRANT_ENABLED = os.getenv("KAI_QDRANT_ENABLED", "0")
KAI_QDRANT_URL = os.getenv("KAI_QDRANT_URL", "http://127.0.0.1:6333")
KAI_QDRANT_COLLECTION = os.getenv("KAI_QDRANT_COLLECTION", "kai_support")
KAI_RERANKER_BACKEND = os.getenv("KAI_RERANKER_BACKEND", "provider")
KAI_GUARDRAILS_ENABLED = os.getenv("KAI_GUARDRAILS_ENABLED", "0")
KAI_TRACING_ENABLED = os.getenv("KAI_TRACING_ENABLED", "0")
KAI_DIAGNOSTIC_EXACT_THRESHOLD = float(os.getenv("KAI_DIAGNOSTIC_EXACT_THRESHOLD", "0.78"))
KAI_CHATWOOT_ENABLED = os.getenv("KAI_CHATWOOT_ENABLED", "0")
KAI_CHATWOOT_API_BASE = os.getenv("KAI_CHATWOOT_API_BASE", "")
KAI_CHATWOOT_API_TOKEN = os.getenv("KAI_CHATWOOT_API_TOKEN", "")
KAI_CHATWOOT_ACCOUNT_ID = os.getenv("KAI_CHATWOOT_ACCOUNT_ID", "")
KAI_CHATWOOT_RESOLUTION_TAG = os.getenv("KAI_CHATWOOT_RESOLUTION_TAG", "faq-ready")
KAI_CHATWOOT_POLL_SECONDS = int(os.getenv("KAI_CHATWOOT_POLL_SECONDS", "300"))
KAI_CHATWOOT_ENFORCE_LIVE_HANDOVER = os.getenv("KAI_CHATWOOT_ENFORCE_LIVE_HANDOVER", "0")
KAI_SOP_WRITEBACK_ENABLED = os.getenv("KAI_SOP_WRITEBACK_ENABLED", "0")
KAI_SOP_MERGE_SYNC_ENABLED = os.getenv("KAI_SOP_MERGE_SYNC_ENABLED", "0")
KAI_SOP_MERGE_SYNC_HOUR = int(os.getenv("KAI_SOP_MERGE_SYNC_HOUR", "8"))
KAI_SOP_MERGE_SYNC_MINUTE = int(os.getenv("KAI_SOP_MERGE_SYNC_MINUTE", "0"))
GOOGLE_DOCS_SOP_DOC_ID = os.getenv("GOOGLE_DOCS_SOP_DOC_ID", "")
TECH_BACKLOG_SHEET_ID = os.getenv("TECH_BACKLOG_SHEET_ID", "")
TECH_BACKLOG_TAB_NAME = os.getenv("TECH_BACKLOG_TAB_NAME", "Chatbot Backlog")
TECH_ACTIVE_TAB_NAME = os.getenv("TECH_ACTIVE_TAB_NAME", "Active")
BUKAPILOT_REPO = os.getenv("BUKAPILOT_REPO", "bukapilot/bukapilot")
BUKAPILOT_BRANCH = os.getenv("BUKAPILOT_BRANCH", "release_ka2")
BUKAPILOT_LOCAL_PATH = os.getenv("BUKAPILOT_LOCAL_PATH", "")

def _split_list(name, default=""):
    return [s.strip() for s in os.getenv(name, default).split(",") if s.strip()]

CS_RECIPIENTS = _split_list("CS_RECIPIENTS")
AGENT_NUMBERS = set(_split_list("AGENT_NUMBERS"))

# Admin
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "changeme-strong")

# Sources
SOP_DOC_URL = os.getenv("SOP_DOC_URL", "")
WARRANTY_CSV_URL = os.getenv("WARRANTY_CSV_URL", "")
GOOGLE_SHEETS_WARRANTY_SHEET_ID = os.getenv("GOOGLE_SHEETS_WARRANTY_SHEET_ID", "")
GOOGLE_SHEETS_WARRANTY_GID = os.getenv("GOOGLE_SHEETS_WARRANTY_GID", "")
GOOGLE_SHEETS_WARRANTY_EXTRA_GID = os.getenv("GOOGLE_SHEETS_WARRANTY_EXTRA_GID", "")
SOP_POLL_SECONDS = int(os.getenv("SOP_POLL_SECONDS", "0"))

# RAG paths
BASE_DIR = os.path.dirname(__file__)
RAG_DIR = os.path.join(BASE_DIR, "rag")
FAISS_DIR = os.path.join(RAG_DIR, "faiss_index")
SOP_JSON_PATH = os.path.join(RAG_DIR, "sop_data.json")

# agent_workspace (content root: core MD, FAQ, skills metadata)
_agent_ws = os.getenv("AGENT_WORKSPACE", "agent_workspace")
AGENT_WORKSPACE = _agent_ws if os.path.isabs(_agent_ws) else os.path.join(BASE_DIR, _agent_ws)
MASTER_FAQ_PATH = os.getenv("MASTER_FAQ_PATH") or os.path.join(
    AGENT_WORKSPACE, "02_knowledge", "faq", "master_faq.md"
)
CONTEXT_REGISTRY_YAML = os.getenv("CONTEXT_REGISTRY_YAML") or os.path.join(
    AGENT_WORKSPACE, "04_context", "context_registry.yaml"
)
WORKSPACE_MANIFEST_PATH = os.path.join(AGENT_WORKSPACE, "00_manifest.md")


def _manifest_rag_source(manifest_path: str) -> str:
    try:
        raw = Path(manifest_path).read_text(encoding="utf-8")
    except Exception:
        return ""
    # Parse YAML-frontmatter-like key line: rag_source: <relative/path.md>
    m = re.search(r"(?m)^\s*rag_source\s*:\s*([^\n#]+?)\s*$", raw)
    if not m:
        return ""
    return m.group(1).strip().strip('"').strip("'")


def resolve_master_faq_path() -> str:
    # Explicit env always wins.
    explicit = os.getenv("MASTER_FAQ_PATH", "").strip()
    if explicit:
        return explicit if os.path.isabs(explicit) else os.path.join(BASE_DIR, explicit)
    rag_rel = _manifest_rag_source(WORKSPACE_MANIFEST_PATH)
    if rag_rel:
        candidate = os.path.join(AGENT_WORKSPACE, rag_rel)
        if os.path.isfile(candidate):
            return candidate
    return MASTER_FAQ_PATH

# Optional web search
BING_API_KEY = os.getenv("BING_API_KEY", "")
VEHICLE_SUPPORT_OFFICIAL_URL = os.getenv("VEHICLE_SUPPORT_OFFICIAL_URL", "https://kommu.ai/support/")
VEHICLE_SUPPORT_HTTP_TIMEOUT_SECONDS = int(os.getenv("VEHICLE_SUPPORT_HTTP_TIMEOUT_SECONDS", "8"))
VEHICLE_SUPPORT_MIN_EVIDENCE_SCORE = float(os.getenv("VEHICLE_SUPPORT_MIN_EVIDENCE_SCORE", "0.65"))
KAI_ROUTE_AGENT_CONFIDENCE_TARGET = float(os.getenv("KAI_ROUTE_AGENT_CONFIDENCE_TARGET", "0.95"))
KAI_ROUTE_AGENT_MAX_STEPS = int(os.getenv("KAI_ROUTE_AGENT_MAX_STEPS", "8"))
KAI_ROUTE_AGENT_DEBUG_ENABLED = os.getenv("KAI_ROUTE_AGENT_DEBUG_ENABLED", "0")
KAI_ROUTE_AGENT_TRACE_MAX_STEPS = int(os.getenv("KAI_ROUTE_AGENT_TRACE_MAX_STEPS", "8"))
KAI_ROUTE_AGENT_VEHICLE_MIN_SCORE = float(os.getenv("KAI_ROUTE_AGENT_VEHICLE_MIN_SCORE", "0.62"))
KAI_BEST_EFFORT_MAX_ASSISTANT_TURNS = int(os.getenv("KAI_BEST_EFFORT_MAX_ASSISTANT_TURNS", "2"))
KAI_FAQ_BEAUTIFY_ENABLED = os.getenv("KAI_FAQ_BEAUTIFY_ENABLED", "1")

# Minimum supported car year 
MIN_SUPPORTED_YEAR = 2016

# Memory settings
MEMORY_DEPTH = int(os.getenv("MEMORY_DEPTH", "10"))
MEMORY_SUMMARY_MAX_CHARS = int(os.getenv("MEMORY_SUMMARY_MAX_CHARS", "1200"))
MEMORY_TTL_PREFERENCES_DAYS = int(os.getenv("MEMORY_TTL_PREFERENCES_DAYS", "365"))
MEMORY_TTL_DEVICE_ACCOUNT_DAYS = int(os.getenv("MEMORY_TTL_DEVICE_ACCOUNT_DAYS", "90"))
MEMORY_TTL_TEMP_ISSUE_DAYS = int(os.getenv("MEMORY_TTL_TEMP_ISSUE_DAYS", "7"))
