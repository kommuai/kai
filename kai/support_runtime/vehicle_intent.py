"""Detect vehicle-support questions so the agent loop can prefetch search_kommu_support."""

from __future__ import annotations

import re

# Common brands in MY market (lowercase tokens).
_MY_VEHICLE_BRANDS = frozenset({
    "proton", "perodua", "toyota", "honda", "nissan", "mazda", "mitsubishi",
    "bmw", "mercedes", "byd", "tesla", "chery", "geely", "volkswagen", "audi",
    "lexus", "hyundai", "kia", "ford", "isuzu", "suzuki", "subaru", "volvo",
    "xpeng", "mg", "mini", "porsche", "land", "rover", "peugeot", "alfa",
    "daihatsu", "haval", "gwm", "omoda", "jaecoo", "denza", "smart",
})

_CATALOG_LIST_RE = re.compile(
    r"\b("
    r"list\s+all|all\s+supported|which\s+cars?|what\s+cars?|"
    r"supported\s+(cars?|vehicles?|models?)|cars?\s+supported|"
    r"vehicle\s+list|models?\s+supported"
    r")\b",
    re.I,
)

_CAR_SUPPORT_MARKERS = (
    "is my car",
    "car supported",
    "vehicle supported",
    "support my",
    "compatible with",
    "compatibility",
    "does kommu work",
    "does ka work",
    "can install on",
    "fit my car",
    "work on my",
    "support proton",
    "support perodua",
    "support toyota",
    "on the list",
    "official list",
)

_YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")

VEHICLE_SUPPORT_TOOL = "search_kommu_support"


def is_catalog_list_query(text: str) -> bool:
    return bool(_CATALOG_LIST_RE.search(text or ""))


def _brands_in_text(text: str) -> list[str]:
    tokens = re.findall(r"[a-z0-9]+", (text or "").lower())
    return [t for t in tokens if t in _MY_VEHICLE_BRANDS]


def should_prefetch_vehicle_support(text: str) -> bool:
    """True when the user message likely needs search_kommu_support before answering."""
    raw = (text or "").strip()
    if not raw:
        return False
    t = raw.lower()

    if is_catalog_list_query(raw):
        return True

    if any(m in t for m in _CAR_SUPPORT_MARKERS):
        return True

    brands = _brands_in_text(t)
    if brands:
        if _YEAR_RE.search(t):
            return True
        if any(w in t for w in ("support", "supported", "compatible", "car", "vehicle", "model")):
            return True

    # Model-like token + year without brand (e.g. "X50 2023 supported?")
    if _YEAR_RE.search(t) and re.search(r"\b[a-z]{2,}\d|\d[a-z]{2,}|[a-z]{2,}\s*(19|20)\d{2}", t):
        if any(w in t for w in ("support", "supported", "compatible", "car")):
            return True

    return False
