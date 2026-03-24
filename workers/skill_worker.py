import asyncio
import logging
from dataclasses import dataclass
from typing import Any

log = logging.getLogger("kai.worker")


@dataclass
class WorkerJob:
    job_id: str
    capability: str
    payload: dict[str, Any]


class SkillWorker:
    """
    Async worker scaffold for heavy capabilities (repo indexing, image/video diagnostics).
    """

    def __init__(self):
        self.queue: asyncio.Queue[WorkerJob] = asyncio.Queue()
        self.running = False

    async def enqueue(self, job: WorkerJob):
        await self.queue.put(job)
        log.info("[Worker] enqueued job=%s capability=%s", job.job_id, job.capability)

    async def start(self):
        self.running = True
        while self.running:
            job = await self.queue.get()
            try:
                await self._run(job)
            except Exception as exc:  # noqa: BLE001
                log.exception("[Worker] job=%s failed err=%s", job.job_id, exc)
            finally:
                self.queue.task_done()

    async def _run(self, job: WorkerJob):
        # Placeholder to be replaced by capability dispatch.
        await asyncio.sleep(0.01)
        log.info("[Worker] completed job=%s capability=%s", job.job_id, job.capability)

    async def stop(self):
        self.running = False

