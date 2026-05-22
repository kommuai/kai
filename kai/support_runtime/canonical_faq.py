"""Shared canonical FAQ lookup (FAQ-first shelf + ReAct loop + search_faq tool)."""

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


def enrich_query_with_history(query: str, history: list[dict] | None) -> str:
    """Append last user turn when the current message is a short follow-up (e.g. video?)."""
    if not history:
        return query
    for turn in reversed(history):
        if (turn.get("role") or "") == "user" and (turn.get("text") or "").strip():
            prev = str(turn.get("text") or "").strip()
            if prev and prev.lower() != (query or "").strip().lower():
                return f"{query}\n\nContext: {prev}"
            break
    return query


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


def format_canonical_hint(hit: dict[str, Any]) -> str:
    iid = hit.get("intent_id") or "faq"
    score = hit.get("score", 0)
    sid = hit.get("source_id") or f"faq:{iid}"
    ans = hit.get("canonical_answer") or ""
    return (
        "### Authoritative FAQ match (use for direct_answer when relevant)\n"
        f"- intent: `{iid}` | source_id: `{sid}` | score: {score:.2f}\n"
        f"- canonical_answer:\n{ans}\n"
        "Quote links and key facts verbatim when this matches the user's question."
    )


def pick_faq_first_runtime(
    search_result: dict[str, Any],
    *,
    wants_video: bool,
    wants_link: bool,
    min_score: float = 0.45,
) -> dict[str, Any] | None:
    """FAQ-first shelf: only when user asked for link/video/guide."""
    if not wants_link:
        return None
    return pick_best_canonical(
        search_result,
        min_score=min_score,
        wants_video=wants_video,
        require_url=True,
    )
