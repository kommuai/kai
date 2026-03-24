import logging
import time
import hmac
from uuid import uuid4

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import PlainTextResponse

from core.policy.settings import RouteMode, get_route_mode
from config import ADMIN_TOKEN, KAI_CHATWOOT_ENFORCE_LIVE_HANDOVER, KAI_ROUTE_AGENT_DEBUG_ENABLED
from lang_detect import is_malay
from services.chatwoot_handover import enforce_live_agent_handover
from services.container import kai_service, support_runtime_service
from session_state import list_faq_candidates, update_faq_candidate_status
from support_runtime.faq_feedback import ingest_tagged_resolutions, publish_candidate_to_faq
from support_runtime.tech_backlog import list_backlog_sheet_tabs

log = logging.getLogger("kai.v2")
router = APIRouter()


def _require_admin(x_admin_token: str | None) -> None:
    token = x_admin_token.strip() if isinstance(x_admin_token, str) else ""
    expected = str(ADMIN_TOKEN or "").strip()
    if not expected or not hmac.compare_digest(token, expected):
        raise HTTPException(status_code=401, detail="Unauthorized admin client")


def _refresh_all_knowledge() -> dict:
    """Single refresh path for active support runtime knowledge."""
    runtime_out = support_runtime_service.refresh_knowledge()
    return {"ok": True, "runtime_refresh": runtime_out}


def _merge_trace(
    payload: dict,
    *,
    trace_id: str,
    mode: RouteMode,
    capability_used: str,
    start: float,
    fallback_reason: str = "",
) -> dict:
    out = dict(payload)
    out.update(
        {
            "trace_id": trace_id,
            "route_mode": mode.value,
            "capability_used": capability_used,
            "latency_ms": int((time.time() - start) * 1000),
        }
    )
    if fallback_reason:
        out["fallback_reason"] = fallback_reason
    return out


def _process_agent_message_data(data: dict) -> dict:
    if not data:
        raise ValueError("Invalid n8n payload")
    msg_type = (data.get("type") or data.get("message_type") or "").strip().lower()
    if msg_type in {"image", "video", "audio", "voice"}:
        payload = {
            "type": "reply",
            "message": (
                "I am a front-line diagnostic AI and do not support image/video/audio analysis yet. "
                "Please describe the issue in text and tell me what car you are driving (brand/model/year)."
            ),
            "next_state": "bot",
        }
        return _merge_trace(
            payload,
            trace_id=str(uuid4()),
            mode=get_route_mode(),
            capability_used="media_capability_guard",
            start=time.time(),
            fallback_reason="media_not_supported_text_only",
        )
    text = data.get("content", "").strip()
    user_id = data.get("phone_number", "unknown")

    start = time.time()
    mode = get_route_mode()
    trace_id = str(uuid4())
    lang = "BM" if is_malay(text) else "EN"

    if not text:
        return _merge_trace({"ok": True}, trace_id=trace_id, mode=mode, capability_used="empty", start=start)

    pre = kai_service.pre_router(data)
    if pre is not None:
        return _merge_trace(pre, trace_id=trace_id, mode=mode, capability_used="pre_router", start=start)

    result = support_runtime_service.execute(text=text, lang=lang, user_id=user_id)
    debug_enabled = str(KAI_ROUTE_AGENT_DEBUG_ENABLED).strip().lower() in {"1", "true", "yes", "on"}
    debug_requested = bool(data.get("debug_route_agent"))
    include_debug = debug_enabled or debug_requested
    if result.decision == "escalate_human":
        enforce = str(KAI_CHATWOOT_ENFORCE_LIVE_HANDOVER).strip().lower() in {"1", "true", "yes", "on"}
        if enforce:
            applied, handover_error = enforce_live_agent_handover(data)
            if not applied:
                payload = {
                    "type": "handover_failed",
                    "message": "Escalation requested but live-agent handover failed. Please retry immediately.",
                    "next_state": "human",
                    "handover_applied": False,
                    "handover_error": handover_error,
                }
                return _merge_trace(
                    payload,
                    trace_id=trace_id,
                    mode=mode,
                    capability_used=result.capability_used or "support_runtime",
                    start=start,
                    fallback_reason=(result.fallback_reason or "escalation_handover_failed"),
                )
        payload = {"type": "handover", "message": result.answer, "next_state": "human", "handover_applied": True}
    else:
        payload = {
            "type": "reply",
            "message": kai_service.add_footer(user_id, result.answer, lang),
            "next_state": "bot",
            "confidence": result.confidence,
            "source_ids": result.source_ids,
            "decision": result.decision,
            "tool_needed": result.tool_needed,
            "escalate_needed": result.escalate_needed,
        }
    if include_debug:
        payload["debug"] = {
            "route_agent": (result.metadata or {}).get("agentic_route", {}),
            "intent_bundle": (result.metadata or {}).get("intent_bundle", {}),
            "evidence": (result.metadata or {}).get("evidence", {}),
        }
    return _merge_trace(
        payload,
        trace_id=trace_id,
        mode=mode,
        capability_used=result.capability_used or "support_runtime",
        start=start,
        fallback_reason=result.fallback_reason or "",
    )


@router.post("/agent/message")
async def agent_message(request: Request):
    data = await request.json()
    try:
        return _process_agent_message_data(data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/v2/agent/message")
async def agent_message_v2(request: Request):
    data = await request.json()
    try:
        out = _process_agent_message_data(data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return out


@router.post("/admin/reset_memory")
async def admin_reset_memory(request: Request, x_admin_token: str | None = Header(default=None)):
    _require_admin(x_admin_token)
    user_id = request.query_params.get("user_id") or (await request.form()).get("user_id")
    msg = kai_service.admin_reset_memory(user_id)
    return PlainTextResponse(msg)


@router.post("/admin/refresh-sop")
def refresh_sop_endpoint(x_admin_token: str | None = Header(default=None)):
    _require_admin(x_admin_token)
    return _refresh_all_knowledge()


@router.post("/admin/faq-feedback/poll")
def admin_poll_faq_feedback(x_admin_token: str | None = Header(default=None)):
    _require_admin(x_admin_token)
    return ingest_tagged_resolutions()


@router.get("/admin/faq-candidates")
def admin_list_faq_candidates(status: str | None = None, x_admin_token: str | None = Header(default=None)):
    _require_admin(x_admin_token)
    return {"ok": True, "items": list_faq_candidates(status=status)}


@router.post("/admin/faq-candidates/{candidate_id}/approve")
def admin_approve_faq_candidate(candidate_id: int, x_admin_token: str | None = Header(default=None)):
    _require_admin(x_admin_token)
    ok = update_faq_candidate_status(candidate_id, "approved")
    return {"ok": ok}


@router.post("/admin/faq-candidates/{candidate_id}/reject")
def admin_reject_faq_candidate(candidate_id: int, x_admin_token: str | None = Header(default=None)):
    _require_admin(x_admin_token)
    ok = update_faq_candidate_status(candidate_id, "rejected")
    return {"ok": ok}


@router.post("/admin/faq-candidates/{candidate_id}/publish")
def admin_publish_faq_candidate(candidate_id: int, x_admin_token: str | None = Header(default=None)):
    _require_admin(x_admin_token)
    result = publish_candidate_to_faq(candidate_id)
    if result.get("ok"):
        result["refresh"] = _refresh_all_knowledge()
    return result


@router.get("/admin/tech-backlog/tabs")
def admin_tech_backlog_tabs(x_admin_token: str | None = Header(default=None)):
    _require_admin(x_admin_token)
    return {"ok": True, "tabs": list_backlog_sheet_tabs()}
