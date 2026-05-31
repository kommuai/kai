"""Admin-controlled FAQ learning: generate proposals from (user_question, admin_answer) pairs."""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from shadou.support_runtime.faq_learn_queue import make_proposal_id, write_proposal
from shadou.support_runtime.providers import build_provider

log = logging.getLogger("shadou.admin_learn")


def _strip_markdown_fences(text: str) -> str:
    s = (text or "").strip()
    if s.startswith("```"):
        lines = s.split("\n")
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        s = "\n".join(lines).strip()
    return s


def _is_plausible_diff(text: str) -> bool:
    t = _strip_markdown_fences(text)
    return bool(t) and "--- " in t and "+++ " in t and "@@" in t


def _extract_json_block(raw: str) -> dict[str, Any] | None:
    m = re.search(r"```json\s*([\s\S]*?)\s*```", raw, re.IGNORECASE)
    if not m:
        m = re.search(r"```\s*([\s\S]*?)\s*```", raw)
    if not m:
        return None
    try:
        data = json.loads(m.group(1).strip())
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _extract_diff(raw: str) -> str:
    for block in re.finditer(r"```(?:diff)?\s*([\s\S]*?)\s*```", raw, re.IGNORECASE):
        candidate = _strip_markdown_fences(block.group(0))
        if _is_plausible_diff(candidate):
            return candidate
    stripped = _strip_markdown_fences(raw)
    if _is_plausible_diff(stripped):
        return stripped
    for line in raw.splitlines():
        if line.startswith("--- "):
            tail = raw[raw.find(line):]
            if _is_plausible_diff(tail):
                return _strip_markdown_fences(tail)
    return ""


def generate_learning_proposal(
    user_question: str,
    admin_answer: str,
    event_meta: dict[str, Any],
) -> dict[str, Any]:
    """Call LLM to generate a FAQ proposal and write it to the learn queue.

    Returns a dict with ok, proposal_id, queue_path.
    """
    from config import resolve_master_faq_path

    provider = build_provider()
    faq_path = Path(resolve_master_faq_path())
    master_body = faq_path.read_text(encoding="utf-8") if faq_path.exists() else ""
    if len(master_body) > 80000:
        master_body = master_body[:80000] + "\n\n[... truncated ...]\n"

    system = (
        "You improve master_faq.md for an AI support agent based on a corrected Q&A pair provided by an admin. "
        "Respond with TWO parts in order:\n"
        "1) A JSON object in a ```json fenced block with keys:\n"
        "   - intent_id (string): existing or new intent slug\n"
        "   - aliases (array of strings): question variants\n"
        "   - answer (string): the correct answer to use\n"
        "2) A valid unified diff (git style) for master_faq.md with "
        "--- a/master_faq.md +++ b/master_faq.md and @@ hunks.\n"
        "Stay faithful to the admin answer; do not invent policy. Prefer small targeted edits."
    )
    user_prompt = (
        f"trigger=admin_learning\n"
        f"user_id={event_meta.get('user_id', '')}\n"
        f"User question:\n{user_question}\n\n"
        f"Admin correct answer:\n{admin_answer}\n\n"
        f"Current master_faq.md (schema: ## intent: id, aliases:, answer:):\n{master_body}\n"
    )

    raw_out = provider.chat(system, user_prompt, temperature=0.1, max_tokens=2048)
    proposal_json = _extract_json_block(raw_out)
    diff_text = _extract_diff(raw_out)

    has_json = isinstance(proposal_json, dict) and bool(proposal_json.get("intent_id"))
    has_diff = bool(diff_text) and _is_plausible_diff(diff_text)

    if not has_json and not has_diff:
        log.warning(
            "admin_learn: LLM output did not contain valid proposal for event_id=%s",
            event_meta.get("event_id", "?"),
        )
        return {"ok": False, "error": "invalid_llm_output"}

    proposal_id = make_proposal_id(event_meta.get("user_id", "admin"), "admin_learning")
    ts = datetime.now(timezone.utc).isoformat()
    meta = {
        "proposal_id": proposal_id,
        "status": "pending",
        "trigger": "admin_learning",
        "user_id": event_meta.get("user_id", ""),
        "event_id": event_meta.get("event_id", ""),
        "created_at": ts,
        "has_diff": has_diff,
        "has_structured": has_json,
    }
    transcript = f"Q: {user_question}\nA: {admin_answer}"
    queue_path = write_proposal(
        proposal_id,
        meta=meta,
        transcript=transcript,
        diff_text=diff_text if has_diff else "",
        proposal=proposal_json if has_json else None,
    )
    log.info("admin_learn: proposal written %s", proposal_id)
    return {"ok": True, "proposal_id": proposal_id, "queue_path": str(queue_path)}
