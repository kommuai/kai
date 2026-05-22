"""WhatsApp / Twilio-safe outbound text (text.body max 4096 chars)."""

from __future__ import annotations

import re

WHATSAPP_MAX_BODY = 4096
_SOFT_TARGET = 1200


def _condense_install_sop(text: str, lang: str) -> str:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    video = next((ln for ln in lines if "youtu" in ln.lower() or "http" in ln.lower()), "")
    bm = (lang or "EN").upper() == "BM"
    if bm:
        head = "Ringkasan pemasangan KommuAssist:"
        tail = "Taip LA jika anda perlukan panduan langkah demi langkah dengan ejen."
    else:
        head = "KommuAssist installation summary:"
        tail = "Type LA if you need a step-by-step walkthrough with an agent."
    parts = [head]
    if video:
        parts.append(video)
    parts.append(tail)
    return "\n\n".join(parts)


def prepare_outbound_reply(body: str, lang: str = "EN") -> tuple[str, dict]:
    """Return (message, metadata) with length within Twilio limits."""
    text = (body or "").strip()
    meta: dict = {"original_len": len(text), "condensed": False, "truncated": False}

    if len(text) <= WHATSAPP_MAX_BODY:
        return text, meta

    lower = text.lower()
    if any(k in lower for k in ("install", "pemasangan", "sop", "step 1", "langkah 1")):
        text = _condense_install_sop(text, lang)
        meta["condensed"] = True

    if len(text) > WHATSAPP_MAX_BODY:
        # Keep opening paragraph + any URLs, drop middle bulk.
        url_pat = re.compile(r"https?://\S+")
        urls = url_pat.findall(text)
        first_block = text.split("\n\n", 1)[0][:800].strip()
        suffix = "\n\n" + "\n".join(urls[:3]) if urls else ""
        tail = (
            "\n\n(Mesej dipendekkan untuk WhatsApp. Taip LA untuk butiran penuh.)"
            if (lang or "EN").upper() == "BM"
            else "\n\n(Message shortened for WhatsApp. Type LA for full details.)"
        )
        budget = WHATSAPP_MAX_BODY - len(suffix) - len(tail) - 20
        text = (first_block[: max(budget, 400)] + suffix + tail).strip()
        meta["truncated"] = True

    if len(text) > WHATSAPP_MAX_BODY:
        text = text[: WHATSAPP_MAX_BODY - 3].rstrip() + "..."
        meta["truncated"] = True

    meta["final_len"] = len(text)
    return text, meta
