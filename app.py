import logging
import os
from datetime import datetime
import json
from logging.handlers import RotatingFileHandler
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi_utils.tasks import repeat_every
import pytz

from api.v2.agent_message import router as v2_message_router
from api.v2.agent_query import router as v2_query_router
from config import (
    KAI_SOP_MERGE_SYNC_ENABLED,
    KAI_SOP_MERGE_SYNC_HOUR,
    KAI_SOP_MERGE_SYNC_MINUTE,
    TZ_REGION,
    WORKSPACE_MANIFEST_PATH,
)
from core.sop_sync_merge import STATE_PATH, sync_sop_regions
from core.workspace_manifest import log_session_store_hint
from services.container import kai_service, support_runtime_service

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


@repeat_every(seconds=600)
def auto_merge_sop_sync():
    if str(KAI_SOP_MERGE_SYNC_ENABLED).strip().lower() not in {"1", "true", "yes", "on"}:
        return
    tz = pytz.timezone(TZ_REGION)
    now = datetime.now(tz)
    if now.hour != int(KAI_SOP_MERGE_SYNC_HOUR) or now.minute != int(KAI_SOP_MERGE_SYNC_MINUTE):
        return
    today = now.strftime("%Y-%m-%d")
    last_sync_date = ""
    if STATE_PATH.exists():
        try:
            state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
            last_sync_date = str(state.get("last_sync_date") or "").strip()
        except Exception:
            last_sync_date = ""
    if last_sync_date == today:
        return
    try:
        out = sync_sop_regions()
        logging.getLogger("kai").info("SOP merge-sync result: %s", out)
    except Exception:
        logging.getLogger("kai").exception("SOP merge-sync failed")