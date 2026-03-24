from __future__ import annotations

import re

from google_sheets import warranty_lookup_by_dongle, warranty_text_from_row
from support_runtime.models import RuntimeResult


def looks_like_dongle(text: str) -> bool:
    t = (text or "").strip()
    if not (6 <= len(t) <= 24):
        return False
    if " " in t:
        return False
    return bool(re.fullmatch(r"[A-Za-z0-9\-_]+", t))


def run_warranty_lookup(text: str, lang: str = "EN") -> RuntimeResult:
    dongle_id = (text or "").strip()
    row = warranty_lookup_by_dongle(dongle_id)
    if not row:
        message = (
            "I could not find warranty details for that dongle ID. Please double-check the ID and try again."
            if lang == "EN"
            else "Saya tidak menjumpai maklumat waranti untuk ID dongle itu. Sila semak semula ID dan cuba lagi."
        )
        return RuntimeResult(
            decision="clarifying_question",
            answer=message,
            confidence=0.82,
            capability_used="legacy_warranty",
            fallback_reason="warranty_not_found",
        )
    text_out = warranty_text_from_row(row)
    answer = f"Warranty status: {text_out}" if lang == "EN" else f"Status waranti: {text_out}"
    return RuntimeResult(
        decision="direct_answer",
        answer=answer,
        confidence=0.95,
        source_ids=["warranty:sheet_lookup"],
        capability_used="legacy_warranty",
    )

