from __future__ import annotations

import os
import time
from contextlib import contextmanager
import logging

log = logging.getLogger("kai.runtime.trace")


def tracing_enabled() -> bool:
    return os.getenv("KAI_TRACING_ENABLED", "0").strip().lower() in {"1", "true", "yes", "on"}


@contextmanager
def trace_span(name: str):
    start = time.time()
    try:
        yield
    finally:
        if tracing_enabled():
            elapsed = int((time.time() - start) * 1000)
            log.info("[Trace] span=%s elapsed_ms=%s", name, elapsed)
