from __future__ import annotations

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


def _configure_logging() -> None:
    os.makedirs("logs", exist_ok=True)
    if logging.getLogger().handlers:
        return
    handler = RotatingFileHandler("logs/kai.log", maxBytes=2_000_000, backupCount=3, encoding="utf-8")
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
    media = Path("media")
    if media.is_dir():
        app.mount("/media", StaticFiles(directory=str(media)), name="media")
    app.include_router(health_router)
    app.include_router(v2_message_router)
    app.include_router(v2_query_router)
    return app
