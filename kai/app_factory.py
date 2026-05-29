from __future__ import annotations

import json
import logging
import os
from contextlib import asynccontextmanager
from logging.handlers import RotatingFileHandler
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from kai.api.health import router as health_router
from kai.api.v2.agent_message import router as v2_message_router
from kai.api.v2.agent_query import router as v2_query_router
from kai.engine.scheduler import start_background_tasks, stop_background_tasks
from kai.engine.startup import run_startup


class _JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "trace_id"):
            payload["trace_id"] = record.trace_id
        return json.dumps(payload, ensure_ascii=False)


def _configure_logging() -> None:
    if logging.getLogger().handlers:
        return
    use_json = os.getenv("KAI_LOG_JSON", "").strip().lower() in {"1", "true", "yes", "on"}
    log_file = os.getenv("KAI_LOG_FILE", "").strip()
    if log_file:
        path = Path(log_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        handler: logging.Handler = RotatingFileHandler(
            path, maxBytes=2_000_000, backupCount=3, encoding="utf-8"
        )
    else:
        handler = logging.StreamHandler()
    if use_json:
        handler.setFormatter(_JsonLogFormatter())
    elif not log_file:
        handler.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
    logging.basicConfig(level=logging.INFO, handlers=[handler])


def _app_title() -> str:
    try:
        from kai.workspace.manifest import load_workspace_manifest

        return f"{load_workspace_manifest().display_name} Support API"
    except Exception:  # noqa: BLE001
        return "Kai Support API"


@asynccontextmanager
async def lifespan(app: FastAPI):
    _configure_logging()
    run_startup()
    tasks = start_background_tasks()
    yield
    await stop_background_tasks(tasks)


def create_app() -> FastAPI:
    app = FastAPI(title=_app_title(), lifespan=lifespan)
    if os.getenv("KAI_MEDIA_PUBLIC", "").strip().lower() in {"1", "true", "yes", "on"}:
        try:
            from kai.settings import get_settings

            media = get_settings().kai_home / "data" / "media"
        except Exception:  # noqa: BLE001
            media = Path("data/media")
        if media.is_dir():
            app.mount("/media", StaticFiles(directory=str(media)), name="media")
    app.include_router(health_router)
    app.include_router(v2_message_router)
    app.include_router(v2_query_router)
    return app
