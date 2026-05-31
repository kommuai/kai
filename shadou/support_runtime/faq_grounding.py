"""Append a review footnote when a direct answer is not backed by FAQ or tool evidence."""

from __future__ import annotations

import re
from typing import Any

from shadou.support_runtime.canonical_faq import pick_best_canonical, result_row_to_canonical
from shadou.workspace.runtime_settings import load_grounded_tools

FOOTNOTE_MARKER = "not in our official FAQ yet"

UNVERIFIED_FOOTNOTE_EN = (
    "\n\n_Note: This detail is not in our official FAQ yet. "
    "A live agent will review when online — type **LA** to speak to someone now._"
)
UNVERIFIED_FOOTNOTE_BM = (
    "\n\n_Nota: Maklumat ini belum ada dalam FAQ rasmi kami. "
    "Ejen langsung akan semak apabila dalam talian — taip **LA** untuk bercakap dengan ejen sekarang._"
)

_FAQ_SOURCE_PREFIXES = ("faq:", "intent:")


def _grounded_tool_ids() -> frozenset[str]:
    return load_grounded_tools()


def _grounded_tool_prefixes() -> tuple[str, ...]:
    return tuple(f"tool:{tid}" for tid in sorted(_grounded_tool_ids()))

_GENERIC_GREETING_RE = re.compile(
    r"^(hi|hello|hai|hey)[!.]?\s*(how can i help|how can i assist|what can i help)",
    re.I,
)


def unverified_footnote(lang: str) -> str:
    return UNVERIFIED_FOOTNOTE_BM if lang == "BM" else UNVERIFIED_FOOTNOTE_EN


def _is_generic_greeting(answer: str) -> bool:
    t = (answer or "").strip()
    if len(t) < 120 and _GENERIC_GREETING_RE.search(t):
        return True
    if len(t) < 80 and re.match(r"^(hi|hello|hai)[!.]?\s*$", t, re.I):
        return True
    return False


def _source_ids_grounded(source_ids: list[str]) -> bool:
    for sid in source_ids or []:
        s = (sid or "").strip().lower()
        if any(s.startswith(p) for p in _FAQ_SOURCE_PREFIXES):
            return True
        if any(s.startswith(p) for p in _grounded_tool_prefixes()):
            return True
    return False


def _observations_grounded(observations: list[dict[str, Any]]) -> bool:
    for obs in observations or []:
        tool = str(obs.get("tool") or "")
        result = obs.get("result") if isinstance(obs.get("result"), dict) else {}
        if not result.get("ok"):
            continue
        if tool == "search_faq":
            best = pick_best_canonical(result, min_score=0.42)
            if best:
                return True
        if tool in _grounded_tool_ids():
            return True
    return False


def _token_set(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]{4,}", (text or "").lower())}


def _answer_aligns_with_canonical(answer: str, canonical: str) -> bool:
    """Heuristic: answer overlaps FAQ wording or repeats a distinctive FAQ phrase."""
    if not canonical or not answer:
        return False
    a = _token_set(answer)
    c = _token_set(canonical)
    if not a or not c:
        return False
    overlap = len(a & c) / max(len(a), 1)
    if overlap >= 0.12:
        return True
    for blob in re.findall(r"https?://\S+|RM\s?[\d,]+", canonical, flags=re.I):
        if blob.lower() in answer.lower():
            return True
    return False


def _retriever_grounded(user_text: str, answer: str, retriever: Any) -> bool:
    if not retriever or not hasattr(retriever, "retrieve"):
        return False
    try:
        items = retriever.retrieve(user_text, top_k=6)
    except Exception:
        return False
    rows = [
        {
            "source_id": r.source_id,
            "text": r.text,
            "score": r.score,
            "metadata": r.metadata,
            "canonical_answer": "",
        }
        for r in items
    ]
    for row in rows:
        hit = result_row_to_canonical(row)
        if hit:
            row["canonical_answer"] = hit["canonical_answer"]
    best = pick_best_canonical({"results": rows}, min_score=0.48)
    if not best:
        return False
    return _answer_aligns_with_canonical(answer, best["canonical_answer"])


def is_answer_faq_grounded(
    *,
    answer: str,
    user_text: str,
    source_ids: list[str] | None = None,
    observations: list[dict[str, Any]] | None = None,
    retriever: Any = None,
) -> bool:
    if _source_ids_grounded(source_ids or []):
        return True
    if _observations_grounded(observations or []):
        return True
    if _retriever_grounded(user_text, answer, retriever):
        return True
    return False


def apply_grounding_footnote_if_needed(
    answer: str,
    *,
    user_text: str,
    lang: str = "EN",
    source_ids: list[str] | None = None,
    observations: list[dict[str, Any]] | None = None,
    retriever: Any = None,
    capability_used: str = "",
    skip_chitchat: bool = False,
) -> str:
    body = (answer or "").rstrip()
    if not body:
        return body
    if capability_used in {"safety_gate", "pre_router", "media_capability_guard"}:
        return body
    if FOOTNOTE_MARKER in body:
        return body
    if skip_chitchat and _is_generic_greeting(body):
        return body
    if is_answer_faq_grounded(
        answer=body,
        user_text=user_text,
        source_ids=source_ids,
        observations=observations,
        retriever=retriever,
    ):
        return body
    footnote = unverified_footnote(lang)
    return body + footnote
