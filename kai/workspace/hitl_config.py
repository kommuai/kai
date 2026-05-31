"""Human-in-the-loop review config from workspace.yaml."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any


@dataclass(frozen=True)
class HitlConfig:
    enabled: bool = True
    confidence_threshold: float = 0.6
    impact_keywords: tuple[str, ...] = (
        "refund",
        "payment",
        "warranty",
        "price",
        "pricing",
        "contract",
        "policy",
        "security",
        "cancel",
        "legal",
        "invoice",
        "billing",
    )
    flag_verification_fail: bool = True
    flag_abstain: bool = True
    flag_escalate: bool = True


def _parse_hitl(workspace_yaml: dict[str, Any]) -> HitlConfig:
    block = workspace_yaml.get("hitl")
    if not isinstance(block, dict):
        return HitlConfig()
    raw_kw = block.get("impact_keywords")
    keywords: tuple[str, ...] = HitlConfig().impact_keywords
    if isinstance(raw_kw, list):
        cleaned = tuple(str(k).strip().lower() for k in raw_kw if str(k).strip())
        if cleaned:
            keywords = cleaned
    try:
        threshold = float(block.get("confidence_threshold", 0.6))
    except (TypeError, ValueError):
        threshold = 0.6
    return HitlConfig(
        enabled=bool(block.get("enabled", True)),
        confidence_threshold=threshold,
        impact_keywords=keywords,
        flag_verification_fail=bool(block.get("flag_verification_fail", True)),
        flag_abstain=bool(block.get("flag_abstain", True)),
        flag_escalate=bool(block.get("flag_escalate", True)),
    )


@lru_cache(maxsize=1)
def get_hitl_config() -> HitlConfig:
    from kai.workspace.manifest import load_workspace_data

    return _parse_hitl(load_workspace_data())


def reload_hitl_config() -> HitlConfig:
    get_hitl_config.cache_clear()
    return get_hitl_config()
