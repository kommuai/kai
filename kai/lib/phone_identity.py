"""Phone / session key normalization (Malaysian mobile, n8n/Chatwoot variants)."""
from __future__ import annotations

import re


def digits_only(value: str) -> str:
    return re.sub(r"\D", "", value or "")


def canonical_my_mobile(raw: str) -> str:
    """Normalize Malaysian mobile to +60XXXXXXXXX for matching."""
    d = digits_only(raw)
    if not d:
        return ""
    if d.startswith("60"):
        return f"+{d}"
    if d.startswith("0"):
        return f"+60{d[1:]}"
    return f"+{d}"


def candidate_user_ids(raw: str) -> list[str]:
    """Possible session keys stored by n8n / Chatwoot."""
    raw = (raw or "").strip()
    canon = canonical_my_mobile(raw)
    d = digits_only(raw)
    out: list[str] = []
    for item in (raw, canon, f"0{canon[3:]}" if canon.startswith("+60") else "", d, f"+{d}"):
        item = (item or "").strip()
        if item and item not in out:
            out.append(item)
    return out
