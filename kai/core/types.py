from dataclasses import dataclass, field
from typing import Any


@dataclass
class CapabilityRequest:
    request_id: str
    user_id: str
    text: str
    lang: str = "EN"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class CapabilityResult:
    ok: bool
    answer: str = ""
    capability_used: str = ""
    confidence: float = 0.0
    sources: list[dict[str, Any]] = field(default_factory=list)
    safety_flags: list[str] = field(default_factory=list)
    fallback_reason: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

