"""WhatsApp / Twilio-safe outbound text (text.body max 4096 chars)."""

from __future__ import annotations

import re

WHATSAPP_MAX_BODY = 4096


def _whatsapp_max_body() -> int:
    try:
        from shadou.workspace.runtime_settings import get_runtime_settings

        return max(500, int(get_runtime_settings().whatsapp_max_reply_chars))
    except Exception:  # noqa: BLE001
        return WHATSAPP_MAX_BODY
_SOFT_TARGET = 1200


def _condense_install_sop(text: str, lang: str) -> str:
    from shadou.content.channels import get_channel_config

    ch = get_channel_config()
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    video = next((ln for ln in lines if "youtu" in ln.lower() or "http" in ln.lower()), "")
    bm = (lang or "EN").upper() == "BM"
    head = ch.install_condense_head_bm if bm else ch.install_condense_head_en
    tail = ch.install_condense_tail_bm if bm else ch.install_condense_tail_en
    parts = [head]
    if video:
        parts.append(video)
    parts.append(tail)
    return "\n\n".join(parts)


def prepare_outbound_reply(body: str, lang: str = "EN") -> tuple[str, dict]:
    """Return (message, metadata) with length within Twilio limits."""
    text = (body or "").strip()
    meta: dict = {"original_len": len(text), "condensed": False, "truncated": False}

    max_body = _whatsapp_max_body()
    if len(text) <= max_body:
        return text, meta

    lower = text.lower()
    if any(k in lower for k in ("install", "pemasangan", "sop", "step 1", "langkah 1")):
        text = _condense_install_sop(text, lang)
        meta["condensed"] = True

    if len(text) > max_body:
        # Keep opening paragraph + any URLs, drop middle bulk.
        url_pat = re.compile(r"https?://\S+")
        urls = url_pat.findall(text)
        first_block = text.split("\n\n", 1)[0][:800].strip()
        suffix = "\n\n" + "\n".join(urls[:3]) if urls else ""
        from shadou.content.channels import get_channel_config

        ch = get_channel_config()
        tail = ch.whatsapp_shortened_tail_bm if (lang or "EN").upper() == "BM" else ch.whatsapp_shortened_tail_en
        budget = max_body - len(suffix) - len(tail) - 20
        text = (first_block[: max(budget, 400)] + suffix + tail).strip()
        meta["truncated"] = True

    if len(text) > max_body:
        text = text[: max_body - 3].rstrip() + "..."
        meta["truncated"] = True

    meta["final_len"] = len(text)
    return text, meta
