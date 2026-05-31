"""DeepSeek API token → USD cost (official rate card).

Source of truth (verified 2026-05-30):
https://api-docs.deepseek.com/quick_start/pricing

Deduction rule (same page): expense = number of tokens × price (per-token rate).
Rates are quoted per 1M tokens; we convert with exact Decimal arithmetic.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

OFFICIAL_PRICING_URL = "https://api-docs.deepseek.com/quick_start/pricing"

# USD per 1,000,000 tokens — from official pricing table.
_RATES_PER_MILLION: dict[str, dict[str, Decimal]] = {
    "deepseek-v4-flash": {
        "input_cache_hit": Decimal("0.0028"),
        "input_cache_miss": Decimal("0.14"),
        "output": Decimal("0.28"),
    },
    # Compatibility aliases (docs: map to v4-flash modes).
    "deepseek-chat": {
        "input_cache_hit": Decimal("0.0028"),
        "input_cache_miss": Decimal("0.14"),
        "output": Decimal("0.28"),
    },
    "deepseek-reasoner": {
        "input_cache_hit": Decimal("0.0028"),
        "input_cache_miss": Decimal("0.14"),
        "output": Decimal("0.28"),
    },
    "deepseek-v4-pro": {
        "input_cache_hit": Decimal("0.0145"),
        "input_cache_miss": Decimal("1.74"),
        "output": Decimal("3.48"),
    },
}

_USD_QUANT = Decimal("0.0000001")  # 7 decimal places for sub-cent precision


@dataclass(frozen=True)
class TokenUsage:
    prompt_tokens: int
    completion_tokens: int
    cached_prompt_tokens: int = 0

    @property
    def uncached_prompt_tokens(self) -> int:
        cached = max(0, min(self.cached_prompt_tokens, self.prompt_tokens))
        return max(0, self.prompt_tokens - cached)

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


@dataclass(frozen=True)
class UsageCost:
    model: str
    usage: TokenUsage
    usd: Decimal
    rates_per_million: dict[str, str]
    pricing_url: str = OFFICIAL_PRICING_URL

    def usd_float(self) -> float:
        return float(self.usd)


def normalize_model_id(model: str) -> str:
    m = (model or "").strip().lower()
    if m in _RATES_PER_MILLION:
        return m
    if m.startswith("deepseek-v4-flash"):
        return "deepseek-v4-flash"
    if m.startswith("deepseek-v4-pro"):
        return "deepseek-v4-pro"
    return m


def rates_for_model(model: str) -> dict[str, Decimal] | None:
    key = normalize_model_id(model)
    return _RATES_PER_MILLION.get(key)


def _per_million_to_usd(tokens: int, rate_per_million: Decimal) -> Decimal:
    if tokens <= 0:
        return Decimal("0")
    return (Decimal(tokens) * rate_per_million) / Decimal(1_000_000)


def compute_usage_cost_usd(model: str, usage: TokenUsage) -> UsageCost:
    """Compute USD cost from token counts using the official per-1M rates."""
    key = normalize_model_id(model)
    rates = _RATES_PER_MILLION.get(key)
    if rates is None:
        raise ValueError(f"No DeepSeek pricing table for model: {model!r}")

    usd = (
        _per_million_to_usd(usage.cached_prompt_tokens, rates["input_cache_hit"])
        + _per_million_to_usd(usage.uncached_prompt_tokens, rates["input_cache_miss"])
        + _per_million_to_usd(usage.completion_tokens, rates["output"])
    ).quantize(_USD_QUANT, rounding=ROUND_HALF_UP)

    return UsageCost(
        model=key,
        usage=usage,
        usd=usd,
        rates_per_million={k: str(v) for k, v in rates.items()},
    )


def parse_openai_usage(usage: Any) -> TokenUsage | None:
    """Parse OpenAI-compatible ``usage`` object (SDK model or dict)."""
    if usage is None:
        return None
    if isinstance(usage, dict):
        prompt = int(usage.get("prompt_tokens") or 0)
        completion = int(usage.get("completion_tokens") or 0)
        details = usage.get("prompt_tokens_details") or {}
        cached = int(details.get("cached_tokens") or 0)
    else:
        prompt = int(getattr(usage, "prompt_tokens", None) or 0)
        completion = int(getattr(usage, "completion_tokens", None) or 0)
        details = getattr(usage, "prompt_tokens_details", None)
        cached = 0
        if details is not None:
            cached = int(getattr(details, "cached_tokens", None) or 0)
    if prompt == 0 and completion == 0:
        return None
    return TokenUsage(
        prompt_tokens=prompt,
        completion_tokens=completion,
        cached_prompt_tokens=cached,
    )
