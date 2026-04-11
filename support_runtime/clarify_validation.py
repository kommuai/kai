"""Validate and normalize clarifying_question outputs (aggressive anti-hedge)."""

from __future__ import annotations

from typing import Any

CLARIFY_MAX_LEN = 360

HEDGE_SNIPPETS: tuple[str, ...] = (
    "want to make sure",
    "accurate info",
    "could you share",
    "one more detail",
    "confirm the facts",
    "just to confirm",
    "so i can",
    "before i can",
    "in order to",
    "to give you accurate",
    "just so i",
    "can i get more",
    "more information",
    "share more detail",
)


def clarify_candidate_from_parsed(parsed: dict[str, Any]) -> str:
    q = str(parsed.get("question") or "").strip()
    if q:
        return q
    return str(parsed.get("answer") or "").strip()


def _has_hedge(text: str) -> bool:
    low = text.lower()
    return any(s in low for s in HEDGE_SNIPPETS)


def is_valid_clarifying_text(text: str) -> tuple[bool, str]:
    t = (text or "").strip()
    if not t:
        return False, "empty"
    if len(t) > CLARIFY_MAX_LEN:
        return False, "too_long"
    if "?" not in t:
        return False, "no_question_mark"
    if _has_hedge(t):
        return False, "hedge"
    return True, ""


def last_question_span(text: str) -> str:
    """Return the last interrogative sentence (from last . or newline before final ?)."""
    t = (text or "").strip()
    if not t:
        return ""
    qpos = t.rfind("?")
    if qpos == -1:
        return t
    start = max(t.rfind(".", 0, qpos), t.rfind("\n", 0, qpos))
    if start < 0:
        return t[: qpos + 1].strip()
    return t[start + 1 : qpos + 1].strip()


REPAIR_USER_PROMPT = (
    "Your previous JSON violated clarifying rules: for clarifying_question you must use "
    'the "question" field with exactly ONE short question (must contain ?), no accuracy '
    "framing, no preamble. Output ONLY JSON:\n"
    '{"action":"final","decision":"clarifying_question","question":"...","confidence":0.55}'
)

COMPRESS_SYSTEM = (
    "You output exactly one short question the user must answer to proceed. "
    "No preamble, no politeness, no JSON. One line ending with ?"
)


def compress_to_one_question(provider: Any, bad_text: str) -> str:
    msgs = [
        {"role": "system", "content": COMPRESS_SYSTEM},
        {"role": "user", "content": (bad_text or "")[:2000]},
    ]
    raw = provider.chat_messages(msgs, temperature=0.0, max_tokens=180)
    line = (raw or "").strip().split("\n", 1)[0].strip()
    return line[:CLARIFY_MAX_LEN]
