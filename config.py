import os
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

def _split_list(name, default=""):
    return [s.strip() for s in os.getenv(name, default).split(",") if s.strip()]

CS_RECIPIENTS = _split_list("CS_RECIPIENTS")
AGENT_NUMBERS = set(_split_list("AGENT_NUMBERS"))

# Admin
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "changeme-strong")

# Sources
SOP_DOC_URL = os.getenv("SOP_DOC_URL", "")
WARRANTY_CSV_URL = os.getenv("WARRANTY_CSV_URL", "")
SOP_POLL_SECONDS = int(os.getenv("SOP_POLL_SECONDS", "0"))

# RAG paths
BASE_DIR = os.path.dirname(__file__)
RAG_DIR = os.path.join(BASE_DIR, "rag")
FAISS_DIR = os.path.join(RAG_DIR, "faiss_index")
SOP_JSON_PATH = os.path.join(RAG_DIR, "sop_data.json")

# Optional web search
BING_API_KEY = os.getenv("BING_API_KEY", "")

# Minimum supported car year 
MIN_SUPPORTED_YEAR = 2016

# Memory settings
MEMORY_DEPTH = 7
