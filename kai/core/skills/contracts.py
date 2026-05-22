from dataclasses import dataclass, field
from typing import Any, Protocol

from kai.core.types import CapabilityRequest, CapabilityResult


@dataclass
class SkillBudget:
    timeout_ms: int = 8000
    retry_count: int = 1
    max_cost_units: int = 10


@dataclass
class SkillContextBundle:
    contexts: dict[str, Any] = field(default_factory=dict)


class Skill(Protocol):
    skill_id: str
    version: str

    def can_handle(self, request: CapabilityRequest, context_meta: dict[str, Any]) -> float:
        ...

    def execute(
        self,
        request: CapabilityRequest,
        context_bundle: SkillContextBundle,
        budget: SkillBudget,
    ) -> CapabilityResult:
        ...

    def degrade(self, reason: str) -> CapabilityResult:
        ...

