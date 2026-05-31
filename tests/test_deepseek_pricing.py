"""Proof tests: USD cost matches DeepSeek official per-1M token rates."""
from __future__ import annotations

from decimal import Decimal

import pytest

from shadou.lib.deepseek_pricing import (
    OFFICIAL_PRICING_URL,
    TokenUsage,
    compute_usage_cost_usd,
    parse_openai_usage,
)


def test_official_url_documented() -> None:
    assert "api-docs.deepseek.com" in OFFICIAL_PRICING_URL


def test_one_million_cache_miss_input_only() -> None:
    """Official: $0.14 per 1M input tokens (cache miss) for deepseek-v4-flash."""
    cost = compute_usage_cost_usd(
        "deepseek-v4-flash",
        TokenUsage(prompt_tokens=1_000_000, completion_tokens=0),
    )
    assert cost.usd == Decimal("0.14")


def test_one_million_output_only() -> None:
    """Official: $0.28 per 1M output tokens for deepseek-v4-flash."""
    cost = compute_usage_cost_usd(
        "deepseek-v4-flash",
        TokenUsage(prompt_tokens=0, completion_tokens=1_000_000),
    )
    assert cost.usd == Decimal("0.28")


def test_one_million_cache_hit_input_only() -> None:
    """Official: $0.0028 per 1M input tokens (cache hit) for deepseek-v4-flash."""
    cost = compute_usage_cost_usd(
        "deepseek-v4-flash",
        TokenUsage(prompt_tokens=1_000_000, completion_tokens=0, cached_prompt_tokens=1_000_000),
    )
    assert cost.usd == Decimal("0.0028")


def test_mixed_cache_hit_and_miss() -> None:
    """Split billing: cached + uncached prompt buckets + output."""
    cost = compute_usage_cost_usd(
        "deepseek-v4-flash",
        TokenUsage(
            prompt_tokens=1_000_000,
            completion_tokens=500_000,
            cached_prompt_tokens=800_000,
        ),
    )
    # 800k hit @ 0.0028/M + 200k miss @ 0.14/M + 500k out @ 0.28/M
    expected = (
        Decimal("800000") * Decimal("0.0028") / Decimal(1_000_000)
        + Decimal("200000") * Decimal("0.14") / Decimal(1_000_000)
        + Decimal("500000") * Decimal("0.28") / Decimal(1_000_000)
    )
    assert cost.usd == expected.quantize(Decimal("0.0000001"))


def test_deepseek_chat_alias_same_as_flash() -> None:
    flash = compute_usage_cost_usd(
        "deepseek-v4-flash",
        TokenUsage(prompt_tokens=10_000, completion_tokens=5_000),
    )
    chat = compute_usage_cost_usd(
        "deepseek-chat",
        TokenUsage(prompt_tokens=10_000, completion_tokens=5_000),
    )
    assert flash.usd == chat.usd


def test_parse_openai_usage_cached_details() -> None:
    usage = parse_openai_usage(
        {
            "prompt_tokens": 1000,
            "completion_tokens": 200,
            "prompt_tokens_details": {"cached_tokens": 600},
        }
    )
    assert usage is not None
    assert usage.cached_prompt_tokens == 600
    assert usage.uncached_prompt_tokens == 400
    cost = compute_usage_cost_usd("deepseek-v4-flash", usage)
    manual = (
        Decimal(600) * Decimal("0.0028") / Decimal(1_000_000)
        + Decimal(400) * Decimal("0.14") / Decimal(1_000_000)
        + Decimal(200) * Decimal("0.28") / Decimal(1_000_000)
    )
    assert cost.usd == manual.quantize(Decimal("0.0000001"))


def test_unknown_model_raises() -> None:
    with pytest.raises(ValueError, match="No DeepSeek pricing"):
        compute_usage_cost_usd("gpt-4o", TokenUsage(1, 1))
