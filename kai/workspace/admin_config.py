"""Admin whitelist and learning config loader from workspace.yaml."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any


@dataclass(frozen=True)
class AdminLearningConfig:
    enabled: bool = True
    min_confidence: float = 0.6
    max_items: int = 10


@dataclass(frozen=True)
class AdminConfig:
    whitelist_numbers: frozenset[str] = field(default_factory=frozenset)
    learning: AdminLearningConfig = field(default_factory=AdminLearningConfig)

    def is_admin(self, phone_number: str) -> bool:
        return bool(phone_number and phone_number in self.whitelist_numbers)


def _parse_admin_config(workspace_yaml: dict[str, Any]) -> AdminConfig:
    block = workspace_yaml.get("admin")
    if not isinstance(block, dict):
        return AdminConfig()
    raw_numbers = block.get("whitelist_numbers") or []
    numbers = frozenset(str(n).strip() for n in raw_numbers if str(n).strip())
    learn_block = block.get("learning")
    if isinstance(learn_block, dict):
        learning = AdminLearningConfig(
            enabled=bool(learn_block.get("enabled", True)),
            min_confidence=float(learn_block.get("min_confidence", 0.6)),
            max_items=int(learn_block.get("max_items", 10)),
        )
    else:
        learning = AdminLearningConfig()
    return AdminConfig(whitelist_numbers=numbers, learning=learning)


@lru_cache(maxsize=1)
def get_admin_config() -> AdminConfig:
    from kai.workspace.manifest import load_workspace_data

    return _parse_admin_config(load_workspace_data())


def reload_admin_config() -> AdminConfig:
    get_admin_config.cache_clear()
    return get_admin_config()
