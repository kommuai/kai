from __future__ import annotations

import threading
from collections import Counter

_lock = threading.Lock()
_counts: Counter[str] = Counter()


def inc(name: str, value: int = 1) -> None:
    with _lock:
        _counts[name] += value


def snapshot() -> dict[str, int]:
    with _lock:
        return dict(_counts)
