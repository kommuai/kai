import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi_utils.tasks import repeat_every

from api.v2.agent_message import router as v2_message_router
from api.v2.agent_query import router as v2_query_router
from config import KAI_CHATWOOT_ENABLED, KAI_CHATWOOT_POLL_SECONDS, WORKSPACE_MANIFEST_PATH
from core.workspace_manifest import log_session_store_hint
from services.container import kai_service, support_runtime_service
from support_runtime.faq_feedback import ingest_tagged_resolutions

os.makedirs("logs", exist_ok=True)
handler = RotatingFileHandler("logs/kai.log", maxBytes=2_000_000, backupCount=3, encoding="utf-8")
logging.basicConfig(level=logging.INFO, handlers=[handler])

app = FastAPI(title="Kai - Kommu Chatbot")
app.mount("/media", StaticFiles(directory="media"), name="media")

app.include_router(v2_message_router)
app.include_router(v2_query_router)


@app.on_event("startup")
def startup_event():
    log_session_store_hint(Path(WORKSPACE_MANIFEST_PATH))
    support_runtime_service.startup()


@repeat_every(seconds=86400)
def auto_refresh():
    support_runtime_service.refresh_knowledge()


@repeat_every(seconds=max(30, KAI_CHATWOOT_POLL_SECONDS))
def auto_ingest_faq_feedback():
    if str(KAI_CHATWOOT_ENABLED).strip().lower() not in {"1", "true", "yes", "on"}:
        return
    try:
        ingest_tagged_resolutions()
    except Exception:
        logging.getLogger("kai").exception("FAQ feedback ingestion failed")