import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi_utils.tasks import repeat_every

from api.v2.agent_message import router as v2_message_router
from api.v2.agent_query import router as v2_query_router
from config import WORKSPACE_MANIFEST_PATH
from core.workspace_manifest import log_session_store_hint
from services.container import kai_service

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
    kai_service.startup()


@repeat_every(seconds=86400)
def auto_refresh():
    kai_service.auto_refresh()