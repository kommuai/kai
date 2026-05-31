"""Create HITL review tickets for low-confidence, high-impact live chat turns."""

from __future__ import annotations

import logging

from shadou.lib.hitl_tickets import create_ticket, ticket_exists_for_turn
from shadou.support_runtime.models import RuntimeResult
from shadou.workspace.admin_config import get_admin_config
from shadou.workspace.hitl_config import get_hitl_config

log = logging.getLogger("shadou.hitl")


def _impact_reasons(question: str, result: RuntimeResult, cfg) -> list[str]:
    reasons: list[str] = []
    q = (question or "").lower()
    for kw in cfg.impact_keywords:
        if kw and kw in q:
            reasons.append(f"keyword:{kw}")
    verification = (result.metadata or {}).get("verification") or {}
    if cfg.flag_verification_fail and verification.get("flagged"):
        reasons.append("verification_failed")
    if cfg.flag_abstain and result.decision == "abstain":
        reasons.append("abstain")
    if cfg.flag_escalate and result.decision == "escalate_human":
        reasons.append("escalate")
    if result.fallback_reason:
        reasons.append(f"fallback:{result.fallback_reason}")
    return reasons


def maybe_record_hitl_ticket(*, user_id: str, user_question: str, result: RuntimeResult) -> str | None:
    """Return ticket_id when a new HITL ticket is created, else None."""
    cfg = get_hitl_config()
    if not cfg.enabled:
        return None

    admin_cfg = get_admin_config()
    if admin_cfg.is_admin(user_id):
        return None

    question = (user_question or "").strip()
    if not question or not user_id:
        return None

    confidence = float(result.confidence or 0.0)
    if confidence >= cfg.confidence_threshold:
        return None

    impact = _impact_reasons(question, result, cfg)
    if not impact:
        return None

    if ticket_exists_for_turn(user_id, question):
        return None

    try:
        ticket_id = create_ticket(
            user_id=user_id,
            user_question=question,
            bot_answer=(result.answer or "").strip(),
            confidence=confidence,
            decision=result.decision or "",
            fallback_reason=result.fallback_reason or "",
            verification_flagged=bool((result.metadata or {}).get("verification", {}).get("flagged")),
            impact_reason=", ".join(impact),
        )
        log.info(
            "hitl ticket created ticket_id=%s user_id=%s confidence=%.2f impact=%s",
            ticket_id,
            user_id,
            confidence,
            impact,
        )
        return ticket_id
    except Exception:
        log.debug("hitl ticket create failed", exc_info=True)
        return None
