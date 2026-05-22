from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


DecisionType = Literal["direct_answer", "clarifying_question", "tool_use", "escalate_human"]
RouteType = Literal[
    "known_faq_intent",
    "troubleshooting_intent",
    "account_order_status_intent",
    "warranty_lookup_intent",
    "vehicle_support_check_intent",
    "unsupported_ambiguous",
    "unsafe_human_escalation",
]


@dataclass
class IntentRecord:
    intent_id: str
    route_type: RouteType
    aliases: list[str]
    canonical_answer: str
    policy_flags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RetrievalItem:
    source_id: str
    text: str
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RuntimeResult:
    decision: DecisionType
    answer: str
    confidence: float
    source_ids: list[str] = field(default_factory=list)
    tool_needed: bool = False
    escalate_needed: bool = False
    capability_used: str = ""
    fallback_reason: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
