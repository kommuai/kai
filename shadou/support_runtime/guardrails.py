from __future__ import annotations

from shadou.settings import get_settings

UNSAFE_TERMS = {"self-harm", "suicide", "hate", "bomb", "kill"}


def safety_gate(text: str) -> tuple[bool, str]:
    if not get_settings().shadou_guardrails_enabled:
        return True, ""
    lower = (text or "").lower()
    for token in UNSAFE_TERMS:
        if token in lower:
            return False, f"unsafe_term:{token}"
    return True, ""
