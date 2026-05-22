from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

from config import (
    AGENT_LEARNT_FAQ_PATH,
    BASE_DIR,
    KAI_CHATWOOT_ACCOUNT_ID,
    KAI_CHATWOOT_API_BASE,
    KAI_CHATWOOT_API_TOKEN,
    KAI_FAQ_LEARN_ENABLED,
    KAI_FAQ_LEARN_FETCH_CHATWOOT,
    KAI_FAQ_LEARN_LEGACY_APPEND,
    KAI_FAQ_LEARN_MASTER_FAQ_MAX_CHARS,
    KAI_FAQ_LEARN_USE_QUEUE,
    KAI_LLM_API_KEY,
    resolve_master_faq_path,
)
from kai.support_runtime.faq_learn_queue import make_proposal_id, write_proposal
from kai.support_runtime.providers import build_provider

log = logging.getLogger("kai.faq_learn")


def _env_truthy(name: str, raw: str) -> bool:
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def _learnt_faq_path() -> Path:
    p = Path(AGENT_LEARNT_FAQ_PATH)
    if not p.is_absolute():
        p = Path(BASE_DIR) / AGENT_LEARNT_FAQ_PATH
    return p


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


def is_plausible_unified_diff(text: str) -> bool:
    t = _strip_markdown_fences(text)
    if not t:
        return False
    return "--- " in t and "+++ " in t and "@@" in t


def _extract_json_proposal(raw_out: str) -> dict[str, Any] | None:
    text = raw_out or ""
    m = re.search(r"```json\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    if not m:
        m = re.search(r"```\s*([\s\S]*?)\s*```", text)
    if not m:
        return None
    try:
        data = json.loads(m.group(1).strip())
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    return data


def _extract_diff_from_output(raw_out: str) -> str:
    text = raw_out or ""
    for block in re.finditer(r"```(?:diff)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE):
        candidate = _strip_markdown_fences(block.group(0))
        if is_plausible_unified_diff(candidate):
            return candidate
    stripped = _strip_markdown_fences(text)
    if is_plausible_unified_diff(stripped):
        return stripped
    for line in text.splitlines():
        if line.startswith("--- "):
            idx = text.find(line)
            tail = text[idx:]
            if is_plausible_unified_diff(tail):
                return _strip_markdown_fences(tail)
    return ""


def fetch_chatwoot_conversation_messages(conversation_id: str) -> list[dict[str, Any]]:
    if not (
        conversation_id
        and KAI_CHATWOOT_API_BASE
        and KAI_CHATWOOT_API_TOKEN
        and KAI_CHATWOOT_ACCOUNT_ID
    ):
        return []
    headers = {"api_access_token": KAI_CHATWOOT_API_TOKEN}
    base = KAI_CHATWOOT_API_BASE.rstrip("/")
    url = f"{base}/api/v1/accounts/{KAI_CHATWOOT_ACCOUNT_ID}/conversations/{conversation_id}/messages"
    try:
        resp = requests.get(url, headers=headers, params={"page": 1}, timeout=25)
        resp.raise_for_status()
        payload = resp.json() if resp.content else {}
    except Exception as exc:  # noqa: BLE001
        log.warning("Chatwoot messages fetch failed: %s", exc)
        return []
    data = payload.get("payload") or payload.get("data") or []
    if isinstance(data, dict):
        data = data.get("messages") or data.get("data") or []
    if not isinstance(data, list):
        return []
    return data


def _format_chatwoot_messages(msgs: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for m in msgs:
        if not isinstance(m, dict):
            continue
        content = (m.get("content") or "").strip()
        if not content:
            continue
        mt = m.get("message_type")
        if mt == 0:
            role = "user"
        elif mt == 1:
            role = "agent"
        else:
            role = "other"
        lines.append(f"{role}: {content}")
    return "\n".join(lines[-200:])


def _format_segment_messages(segment: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for m in segment:
        role = str(m.get("role") or "user")
        text = (m.get("text") or "").strip()
        if text:
            lines.append(f"{role}: {text}")
    return "\n".join(lines)


def build_learn_transcript(
    segment_messages: list[dict[str, Any]],
    cw_conversation_id: str,
) -> str:
    if cw_conversation_id and _env_truthy("KAI_FAQ_LEARN_FETCH_CHATWOOT", KAI_FAQ_LEARN_FETCH_CHATWOOT):
        raw = fetch_chatwoot_conversation_messages(cw_conversation_id)
        if raw:
            return _format_chatwoot_messages(raw)
    return _format_segment_messages(segment_messages)


def run_faq_learn(
    user_id: str,
    segment_messages: list[dict[str, Any]],
    cw_conversation_id: str,
    *,
    trigger: str = "resume",
) -> dict[str, Any]:
    if not _env_truthy("KAI_FAQ_LEARN_ENABLED", KAI_FAQ_LEARN_ENABLED):
        return {"ok": False, "skipped": "disabled"}
    if not (KAI_LLM_API_KEY or "").strip():
        return {"ok": False, "skipped": "no_llm_key"}

    transcript = build_learn_transcript(segment_messages, cw_conversation_id)
    if not transcript.strip():
        return {"ok": False, "skipped": "empty_transcript"}

    faq_path = Path(resolve_master_faq_path())
    master_raw = faq_path.read_text(encoding="utf-8") if faq_path.exists() else ""
    max_c = max(5000, int(KAI_FAQ_LEARN_MASTER_FAQ_MAX_CHARS))
    truncated = False
    if len(master_raw) > max_c:
        master_body = master_raw[:max_c] + "\n\n[... truncated for model context ...]\n"
        truncated = True
    else:
        master_body = master_raw

    provider = build_provider()
    system = (
        "You improve master_faq.md for a support bot after a human handoff session. "
        "Respond with TWO parts in order:\n"
        "1) A JSON object in a ```json fenced block with keys:\n"
        "   - summary (string): what the human/agent resolved\n"
        "   - intent_updates (array): each item has intent_id (required), and any of "
        "aliases, aliases_add, answer, answer_append, answer_replace\n"
        "   - pitfalls (array of strings): mistakes the bot should avoid\n"
        "2) A valid unified diff (git style) for master_faq.md with --- a/master_faq.md "
        "+++ b/master_faq.md and @@ hunks.\n"
        "Stay faithful to the transcript; do not invent policy. Prefer small targeted edits."
    )
    user_prompt = (
        f"trigger={trigger}\n"
        f"user_id={user_id}\n"
        f"chatwoot_conversation_id={cw_conversation_id or 'none'}\n"
        f"transcript:\n{transcript}\n\n"
        f"Current master_faq.md (schema: ## intent: id, aliases:, answer:):\n{master_body}\n"
    )
    raw_out = provider.chat(system, user_prompt, temperature=0.1, max_tokens=4096)
    proposal_json = _extract_json_proposal(raw_out)
    diff_text = _extract_diff_from_output(raw_out)

    has_json = isinstance(proposal_json, dict) and bool(proposal_json.get("intent_updates"))
    has_diff = bool(diff_text) and is_plausible_unified_diff(diff_text)
    if not has_json and not has_diff:
        log.warning("FAQ learn rejected output for user_id=%s trigger=%s", user_id, trigger)
        return {"ok": False, "error": "invalid_learn_output"}

    proposal_id = make_proposal_id(user_id, trigger)
    ts = datetime.now(timezone.utc).isoformat()
    meta = {
        "proposal_id": proposal_id,
        "status": "pending",
        "trigger": trigger,
        "user_id": user_id,
        "chatwoot_conversation_id": cw_conversation_id or "",
        "created_at": ts,
        "truncated_master": truncated,
        "has_diff": has_diff,
        "has_structured": has_json,
    }
    queue_path: str | None = None
    if _env_truthy("KAI_FAQ_LEARN_USE_QUEUE", KAI_FAQ_LEARN_USE_QUEUE):
        qdir = write_proposal(
            proposal_id,
            meta=meta,
            transcript=transcript,
            diff_text=diff_text if has_diff else "",
            proposal=proposal_json if has_json else None,
        )
        queue_path = str(qdir)

    legacy_path: str | None = None
    if _env_truthy("KAI_FAQ_LEARN_LEGACY_APPEND", KAI_FAQ_LEARN_LEGACY_APPEND) and has_diff:
        out_path = _learnt_faq_path()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        header = (
            f"\n\n<!-- learn: ts={ts} proposal={proposal_id} user_id={user_id} "
            f"cw_conv={cw_conversation_id or '-'} trigger={trigger} "
            f"truncated_master={truncated} -->\n"
        )
        with out_path.open("a", encoding="utf-8") as f:
            f.write(header)
            f.write(diff_text.rstrip() + "\n")
        legacy_path = str(out_path)

    return {
        "ok": True,
        "proposal_id": proposal_id,
        "queue_path": queue_path,
        "legacy_path": legacy_path,
    }
