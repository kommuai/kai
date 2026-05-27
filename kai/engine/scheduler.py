from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from typing import Any

import pytz

async def _sleep(seconds: float) -> None:
    try:
        await asyncio.sleep(seconds)
    except asyncio.CancelledError:
        raise


async def daily_knowledge_refresh_loop() -> None:
    from kai.engine.refresh import refresh_runtime_knowledge

    log = logging.getLogger("kai.scheduler")
    while True:
        await _sleep(86400)
        try:
            out = refresh_runtime_knowledge(compile_kb=True)
            log.info("scheduled knowledge refresh: %s", out)
        except Exception:
            log.exception("scheduled knowledge refresh failed")


async def sop_merge_sync_loop() -> None:
    from config import KAI_SOP_MERGE_SYNC_HOUR, KAI_SOP_MERGE_SYNC_MINUTE, KAI_SOP_MERGE_SYNC_ENABLED, TZ_REGION
    from kai.core.sop_sync_merge import state_path, sync_sop_regions

    if str(KAI_SOP_MERGE_SYNC_ENABLED).strip().lower() not in {"1", "true", "yes", "on"}:
        return

    log = logging.getLogger("kai.scheduler")
    tz = pytz.timezone(TZ_REGION)
    target_h = int(KAI_SOP_MERGE_SYNC_HOUR)
    target_m = int(KAI_SOP_MERGE_SYNC_MINUTE)

    while True:
        await _sleep(600)
        now = datetime.now(tz)
        if now.hour != target_h or now.minute != target_m:
            continue
        today = now.strftime("%Y-%m-%d")
        last_sync_date = ""
        sp = state_path()
        if sp.exists():
            try:
                state = json.loads(sp.read_text(encoding="utf-8"))
                last_sync_date = str(state.get("last_sync_date") or "").strip()
            except Exception:
                last_sync_date = ""
        if last_sync_date == today:
            continue
        try:
            out = sync_sop_regions()
            log.info("scheduled SOP merge-sync: %s", out)
        except Exception:
            log.exception("scheduled SOP merge-sync failed")


def _scheduler_enabled() -> bool:
    import os

    return os.getenv("KAI_SCHEDULER_ENABLED", "1").strip().lower() not in {"0", "false", "no", "off"}


def start_background_tasks() -> list[asyncio.Task[Any]]:
    if not _scheduler_enabled():
        return []
    tasks: list[asyncio.Task[Any]] = []
    tasks.append(asyncio.create_task(daily_knowledge_refresh_loop(), name="kai-daily-refresh"))
    from kai.engine.features import sop_merge_scheduler_enabled

    if sop_merge_scheduler_enabled():
        tasks.append(asyncio.create_task(sop_merge_sync_loop(), name="kai-sop-sync"))
    return tasks


async def stop_background_tasks(tasks: list[asyncio.Task[Any]]) -> None:
    for task in tasks:
        task.cancel()
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)
