"""Shared canonical FAQ helpers for search_faq tool output."""

from __future__ import annotations

import re
from typing import Any


def extract_answer_from_chunk(text: str) -> str:
    t = (text or "").strip()
    if not t:
        return ""
    m = re.search(r"(?:^|\n)A:\s*(.*)\s*$", t, flags=re.S)
    if m:
        return (m.group(1) or "").strip()
    return t


def result_row_to_canonical(row: dict[str, Any]) -> dict[str, Any] | None:
    if not isinstance(row, dict):
        return None
    meta = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
    if meta.get("category") != "known_faq_intent":
        return None
    score = float(row.get("score") or 0.0)
    ans = (row.get("canonical_answer") or "").strip() or extract_answer_from_chunk(str(row.get("text") or ""))
    if not ans:
        return None
    intent_id = str(meta.get("intent_id") or row.get("source_id") or "").replace("faq:", "")
    return {
        "intent_id": intent_id,
        "canonical_answer": ans,
        "source_id": str(row.get("source_id") or f"faq:{intent_id}"),
        "score": score,
    }


def pick_best_canonical(
    search_result: dict[str, Any],
    *,
    min_score: float = 0.42,
    wants_video: bool = False,
    require_url: bool = False,
) -> dict[str, Any] | None:
    """Best known_faq_intent hit from a search_faq payload."""
    best: dict[str, Any] | None = None
    best_score = -1.0
    for row in (search_result.get("results") or [])[:6]:
        hit = result_row_to_canonical(row)
        if not hit or hit["score"] < min_score:
            continue
        ans = hit["canonical_answer"].lower()
        if require_url and "http://" not in ans and "https://" not in ans:
            continue
        if wants_video and "youtu" not in ans and "video" not in ans:
            continue
        if hit["score"] > best_score:
            best_score = hit["score"]
            best = hit
    return best
