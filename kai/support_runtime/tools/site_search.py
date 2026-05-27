from __future__ import annotations

import html
import re
from functools import lru_cache
from typing import Any

import requests


def strip_html(raw: str) -> str:
    txt = html.unescape(raw or "")
    txt = re.sub(r"(?is)<script.*?>.*?</script>", " ", txt)
    txt = re.sub(r"(?is)<style.*?>.*?</style>", " ", txt)
    txt = re.sub(r"(?s)<[^>]+>", " ", txt)
    return re.sub(r"\s+", " ", txt).strip()


@lru_cache(maxsize=4)
def support_site_corpus(url: str, timeout: int = 8) -> str:
    if not url:
        return ""
    try:
        resp = requests.get(url, timeout=timeout, headers={"User-Agent": "KaiSupportBot/2.0"})
        if not resp.ok:
            return ""
        return strip_html(resp.text)
    except Exception:
        return ""


_VEHICLE_QUERY_ALIASES: dict[str, str] = {
    "cr-v": "crv",
    "crv5": "crv gen 5",
    "cr-v5": "crv gen 5",
    "hr-v": "hrv",
    "atto3": "atto 3",
    "sealion7": "sealion 7",
    "x50fl": "x50 fl",
    "x70fl": "x70 fl",
    "cityfl": "city fl",
}

_VEHICLE_QUERY_STOPWORDS: frozenset[str] = frozenset({
    "is", "my", "car", "support", "supported", "do", "you", "can", "vehicle",
    "the", "a", "with", "have", "has", "does", "it", "for", "of", "on",
})


def _normalize_vehicle_query(text: str) -> str:
    t = (text or "").lower().strip()
    for alias, replacement in _VEHICLE_QUERY_ALIASES.items():
        t = re.sub(r"\b" + re.escape(alias) + r"\b", replacement, t)
    return t


def _expand_years(raw: str) -> set[int]:
    text = str(raw or "")
    years: set[int] = set()
    for a, b in re.findall(r"((?:19|20)\d{2})\s*[–-]\s*((?:19|20)\d{2})", text):
        years.update(range(int(a), int(b) + 1))
    for y in re.findall(r"\b((?:19|20)\d{2})\b", text):
        years.add(int(y))
    return {y for y in years if 1980 <= y <= 2035}


@lru_cache(maxsize=2)
def _load_vehicle_catalog(vehicles_json_url: str, timeout: int) -> list[dict[str, Any]]:
    if not vehicles_json_url:
        return []
    try:
        resp = requests.get(vehicles_json_url, timeout=timeout)
        if not resp.ok:
            return []
        obj = resp.json()
    except Exception:
        return []

    items: list[dict[str, Any]] = []
    if isinstance(obj, dict):
        for v in obj.values():
            if isinstance(v, list):
                items.extend([x for x in v if isinstance(x, dict)])
    elif isinstance(obj, list):
        items = [x for x in obj if isinstance(x, dict)]

    rows: list[dict[str, Any]] = []
    for row in items:
        brand = str(row.get("brand") or "").strip()
        model = str(row.get("model") or "").strip()
        if not (brand or model):
            continue
        years = _expand_years(row.get("year") or "")
        variant = str(row.get("variant") or "").strip()
        search_text = _normalize_vehicle_query(f"{brand} {model} {variant}")
        rows.append(
            {
                "name": f"{brand} {model}".strip(),
                "years": years,
                "variant": variant,
                "search_words": set(search_text.split()),
                "model_words": set(model.lower().split()),
            }
        )
    return rows


def match_vehicle_catalog(
    query: str,
    *,
    vehicles_json_url: str = "",
    timeout: int = 8,
) -> dict[str, Any] | None:
    vehicles = _load_vehicle_catalog(vehicles_json_url, timeout)
    if not vehicles:
        return None
    q = _normalize_vehicle_query(query)
    if not q:
        return None
    year_m = re.search(r"\b(19|20)\d{2}\b", q)
    q_year = int(year_m.group(0)) if year_m else None
    q_tokens = [
        t for t in re.split(r"[^a-z0-9]+", q)
        if len(t) >= 2 and t not in _VEHICLE_QUERY_STOPWORDS
    ]
    if not q_tokens:
        return None

    best = None
    best_score = -1
    for row in vehicles:
        search_words: set[str] = row.get("search_words") or set()
        model_words: set[str] = row.get("model_words") or set()
        token_hits = sum(1 for t in q_tokens if t in search_words)
        has_model_hit = any(t in model_words for t in q_tokens)
        if token_hits < (1 if has_model_hit else 2):
            continue
        years = row.get("years") or set()
        if q_year is not None and years and q_year not in years:
            continue
        score = token_hits + (2 if q_year is not None and q_year in years else 0)
        if score > best_score:
            best_score = score
            best = row
    return best
