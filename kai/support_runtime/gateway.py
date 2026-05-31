"""Unified support turn: session gates + ReAct runtime + optional grounding."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from kai.content.channels import get_channel_config
from kai.lib.lang import resolve_lang
from kai.services.container import kai_service, support_runtime_service
from kai.support_runtime.faq_grounding import apply_grounding_footnote_if_needed, is_answer_faq_grounded
from kai.support_runtime.agent_loop import _looks_like_chitchat
from kai.support_runtime.metrics import record_turn_metrics
from kai.support_runtime.models import RuntimeResult
from kai.support_runtime.hitl import maybe_record_hitl_ticket
from kai.support_runtime.verifier import verify_result
from kai.workspace.runtime_settings import get_runtime_settings


@dataclass
class SupportTurnOutcome:
    """Result of one user message through gates + runtime."""

    kind: str  # reply | handover | frozen | empty | pre_ok
    message: str
    runtime: RuntimeResult | None = None
    next_state: str = "bot"
    pre_router: dict[str, Any] | None = None

    def to_inbound_json(self) -> dict[str, Any]:
        if self.kind == "empty":
            return {"ok": True, "answer": "", "decision": "", "escalate_needed": False, "skip_send": True}
        if self.runtime is not None:
            return {
                "ok": True,
                "answer": self.message,
                "decision": self.runtime.decision or "",
                "escalate_needed": bool(self.runtime.escalate_needed),
                "skip_send": not (self.message or "").strip(),
            }
        return {
            "ok": True,
            "answer": self.message,
            "decision": self.kind,
            "escalate_needed": self.kind == "handover",
            "skip_send": not (self.message or "").strip(),
        }


def _maybe_force_abstain(result: RuntimeResult, text: str, lang: str) -> RuntimeResult:
    """Force decision to abstain when confidence is below threshold and evidence is absent."""
    if result.decision != "direct_answer":
        return result
    rs = get_runtime_settings()
    if result.confidence >= rs.eval_abstain_threshold:
        return result
    observations = ((result.metadata or {}).get("evidence") or {}).get("observations") or []
    if is_answer_faq_grounded(
        answer=result.answer,
        user_text=text,
        source_ids=result.source_ids,
        observations=observations,
    ):
        return result
    copy = rs.eval_abstain_copy_bm if lang == "BM" else rs.eval_abstain_copy_en
    from dataclasses import replace
    return replace(
        result,
        decision="abstain",
        answer=copy,
        fallback_reason="low_confidence_no_evidence",
    )


def run_support_turn(
    *,
    user_id: str,
    text: str,
    lang: str | None = None,
    use_pre_router: bool = True,
    apply_grounding: bool = True,
) -> SupportTurnOutcome:
    """Single entry for WhatsApp, HTTP, and query APIs."""
    from kai.lib.llm_usage_record import resolve_usage_tenant_slug, set_usage_context

    set_usage_context(tenant_slug=resolve_usage_tenant_slug(), source="engine_chat")

    text = (text or "").strip()
    user_id = (user_id or "").strip()
    lang = lang or resolve_lang(user_id=user_id)
    ch = get_channel_config()

    if not text:
        guard = ch.media_guard_en if lang == "EN" else ch.media_guard_bm
        return SupportTurnOutcome(kind="empty", message=guard)

    if use_pre_router:
        pre = kai_service.pre_router({"content": text, "phone_number": user_id or "unknown"})
        if pre is not None:
            if pre.get("ok") is True and not pre.get("type"):
                return SupportTurnOutcome(kind="pre_ok", message="", pre_router=pre)
            ptype = str(pre.get("type") or "reply")
            msg = str(pre.get("message") or "")
            nstate = str(pre.get("next_state") or ("human" if ptype in ("handover", "frozen") else "bot"))
            return SupportTurnOutcome(kind=ptype, message=msg, next_state=nstate, pre_router=pre)

    result = support_runtime_service.execute(text=text, lang=lang, user_id=user_id)
    result = verify_result(result)
    result = _maybe_force_abstain(result, text, lang)
    maybe_record_hitl_ticket(user_id=user_id, user_question=text, result=result)

    if result.decision == "escalate_human":
        from kai.lib.session_state import freeze

        freeze(user_id, True)
        msg = kai_service.finalize_reply(user_id, result.answer, lang, suppress=True)
        return SupportTurnOutcome(kind="handover", message=msg, runtime=result, next_state="human")

    if result.decision == "abstain":
        record_turn_metrics(result)
        msg = kai_service.finalize_reply(user_id, result.answer, lang, suppress=True)
        return SupportTurnOutcome(kind="reply", message=msg, runtime=result, next_state="bot")

    answer_text = result.answer or ""
    if apply_grounding and result.decision == "direct_answer":
        observations = ((result.metadata or {}).get("evidence") or {}).get("observations") or []
        answer_text = apply_grounding_footnote_if_needed(
            answer_text,
            user_text=text,
            lang=lang,
            source_ids=result.source_ids,
            observations=observations,
            retriever=support_runtime_service.retriever,
            capability_used=result.capability_used or "",
            skip_chitchat=_looks_like_chitchat(text),
        )

    suppress_footer = result.decision in ("direct_answer", "clarifying_question")
    msg = kai_service.finalize_reply(user_id, answer_text, lang, suppress=suppress_footer)
    record_turn_metrics(result)
    return SupportTurnOutcome(kind="reply", message=msg, runtime=result, next_state="bot")
