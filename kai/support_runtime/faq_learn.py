from __future__ import annotations

import logging
import threading
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
    KAI_FAQ_LEARN_ASYNC,
    KAI_FAQ_LEARN_ENABLED,
    KAI_FAQ_LEARN_FETCH_CHATWOOT,
    KAI_FAQ_LEARN_MASTER_FAQ_MAX_CHARS,
    KAI_LLM_API_KEY,
    resolve_master_faq_path,
)
from kai.lib.session_state import pop_human_segment_for_learn
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
        "You propose minimal edits to master_faq.md so the support bot answers better next time. "
        "Output ONLY a valid unified diff (git style) that would apply to the file master_faq.md. "
        "Use --- a/master_faq.md and +++ b/master_faq.md headers and @@ hunks. "
        "Do not add commentary outside the patch. Prefer small, targeted changes to existing intents "
        "or one new ## intent: block if needed. Stay faithful to facts from the transcript; do not invent policy."
    )
    user_prompt = (
        f"user_id={user_id}\n"
        f"chatwoot_conversation_id={cw_conversation_id or 'none'}\n"
        f"transcript:\n{transcript}\n\n"
        f"Current master_faq.md (schema: ## intent: id, aliases:, answer:):\n{master_body}\n"
    )
    raw_out = provider.chat(system, user_prompt, temperature=0.1, max_tokens=4096)
    diff_text = _strip_markdown_fences(raw_out)
    if not is_plausible_unified_diff(diff_text):
        log.warning("FAQ learn rejected non-diff output for user_id=%s", user_id)
        return {"ok": False, "error": "invalid_diff_shape"}

    out_path = _learnt_faq_path()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    header = (
        f"\n\n<!-- learn: ts={ts} user_id={user_id} cw_conv={cw_conversation_id or '-'} "
        f"truncated_master={truncated} -->\n"
    )
    with out_path.open("a", encoding="utf-8") as f:
        f.write(header)
        f.write(diff_text.rstrip() + "\n")

    return {"ok": True, "path": str(out_path)}


def schedule_faq_learn_after_handback(user_id: str) -> None:
    """Pop segment from session and run FAQ learn (async by default)."""
    messages, cw_id = pop_human_segment_for_learn(user_id)
    if not messages and not cw_id:
        return

    def job() -> None:
        try:
            out = run_faq_learn(user_id, messages, cw_id)
            log.info("faq_learn result user_id=%s %s", user_id, out)
        except Exception as exc:  # noqa: BLE001
            log.exception("faq_learn failed user_id=%s: %s", user_id, exc)

    if _env_truthy("KAI_FAQ_LEARN_ASYNC", KAI_FAQ_LEARN_ASYNC):
        threading.Thread(target=job, daemon=True).start()
    else:
        job()
