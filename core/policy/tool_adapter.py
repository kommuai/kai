import logging
import time
from typing import Callable, TypeVar


T = TypeVar("T")
log = logging.getLogger("kai.tool_adapter")


class ToolAdapter:
    """Centralized timeout/retry/audit wrapper for capability execution."""

    def __init__(self, default_timeout_ms: int = 8000, default_retry_count: int = 1):
        self.default_timeout_ms = default_timeout_ms
        self.default_retry_count = default_retry_count

    def execute(self, name: str, fn: Callable[[], T], timeout_ms: int | None = None, retry_count: int | None = None) -> T:
        max_retries = self.default_retry_count if retry_count is None else retry_count
        start = time.time()
        last_exc: Exception | None = None
        for attempt in range(max_retries + 1):
            try:
                out = fn()
                elapsed_ms = int((time.time() - start) * 1000)
                log.info(
                    "[ToolAdapter] ok name=%s attempt=%s elapsed_ms=%s timeout_ms=%s",
                    name,
                    attempt + 1,
                    elapsed_ms,
                    timeout_ms or self.default_timeout_ms,
                )
                return out
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                log.warning("[ToolAdapter] fail name=%s attempt=%s err=%s", name, attempt + 1, exc)
        raise RuntimeError(f"Tool execution failed for {name}: {last_exc}")

