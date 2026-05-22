from __future__ import annotations

import os


UNSAFE_TERMS = {"self-harm", "suicide", "hate", "bomb", "kill"}


def safety_gate(text: str) -> tuple[bool, str]:
    if os.getenv("KAI_GUARDRAILS_ENABLED", "0").strip().lower() not in {"1", "true", "yes", "on"}:
        return True, ""
    lower = (text or "").lower()
    for token in UNSAFE_TERMS:
        if token in lower:
            return False, f"unsafe_term:{token}"
    return True, ""
