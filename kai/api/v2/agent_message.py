import logging
import time
import hmac
from uuid import uuid4

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import PlainTextResponse

from kai.core.policy.settings import RouteMode, get_route_mode
from kai.content.channels import get_channel_config
from kai.engine.metrics import inc as metrics_inc
from kai.engine.refresh import refresh_runtime_knowledge
from kai.settings import get_settings

from kai.lib.lang_detect import is_malay
from kai.services.chatwoot_handover import (
    enforce_live_agent_handover,
    extract_chatwoot_conversation_id,
)
from kai.services.container import kai_service, support_runtime_service
from kai.lib.session_state import append_human_segment_turn, freeze, start_human_segment

log = logging.getLogger("kai.v2")
router = APIRouter()

_SAFE_ERROR_REPLY = (
    "Sorry, something went wrong on our side. Please try again in a moment or type LA for a live agent."
)


def _require_admin(x_admin_token: str | None) -> None:
    token = x_admin_token.strip() if isinstance(x_admin_token, str) else ""
    expected = str(get_settings().admin_token or "").strip()
    if not expected or not hmac.compare_digest(token, expected):
        raise HTTPException(status_code=401, detail="Unauthorized admin client")


def _admin_token_valid(x_admin_token: str | None) -> bool:
    token = x_admin_token.strip() if isinstance(x_admin_token, str) else ""
    expected = str(get_settings().admin_token or "").strip()
    return bool(expected) and hmac.compare_digest(token, expected)


def _refresh_all_knowledge() -> dict:
    return refresh_runtime_knowledge(compile_kb=True)


def _merge_trace(
    payload: dict,
    *,
    trace_id: str,
    mode: RouteMode,
    capability_used: str,
    start: float,
    fallback_reason: str = "",
) -> dict:
    payload = dict(payload)
    payload["trace_id"] = trace_id
    payload["route_mode"] = mode.value if hasattr(mode, "value") else str(mode)
    payload["capability_used"] = capability_used
    payload["latency_ms"] = int((time.time() - start) * 1000)
    if fallback_reason:
        payload["fallback_reason"] = fallback_reason
    return payload


def _process_agent_message_data(data: dict, *, x_admin_token: str | None = None) -> dict:
    if not isinstance(data, dict):
        raise ValueError("payload_must_be_object")

    ch = get_channel_config()
    if data.get("media_url") and not ch.allow_media:
        start = time.time()
        payload = {
            "type": "reply",
            "message": ch.media_fallback_message("EN"),
            "next_state": "bot",
        }
        return _merge_trace(
            payload,
            trace_id=str(uuid4()),
            mode=get_route_mode(),
            capability_used="media_capability_guard",
            start=start,
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

    metrics_inc("agent_message.requests")
    s = get_settings()
    pre = kai_service.pre_router(data)
    if pre is not None:
        if pre.get("type") == "handover" and bool(s.kai_chatwoot_enforce_live_handover):
            applied, handover_error = enforce_live_agent_handover(data)
            pre = dict(pre)
            if applied:
                pre["handover_applied"] = True
            else:
                pre = {
                    "type": "handover_failed",
                    "message": (
                        "Live-agent handover was requested but could not be completed. "
                        "Please retry or contact support."
                    ),
                    "next_state": "human",
                    "handover_applied": False,
                    "handover_error": handover_error,
                }
        return _merge_trace(pre, trace_id=trace_id, mode=mode, capability_used="pre_router", start=start)

    try:
        result = support_runtime_service.execute(text=text, lang=lang, user_id=user_id)
    except Exception:
        metrics_inc("agent_message.runtime_errors")
        log.exception("support_runtime.execute failed trace_id=%s user_id=%s", trace_id, user_id)
        payload = {
            "type": "reply",
            "message": _SAFE_ERROR_REPLY,
            "next_state": "bot",
            "decision": "escalate_human",
            "escalate_needed": True,
        }
        return _merge_trace(
            payload,
            trace_id=trace_id,
            mode=mode,
            capability_used="support_runtime_error",
            start=start,
            fallback_reason="runtime_exception",
        )

    debug_env = bool(s.kai_route_agent_debug_enabled)
    debug_requested = bool(data.get("debug_route_agent"))
    include_debug = debug_env and (debug_requested and _admin_token_valid(x_admin_token))

    if result.decision == "escalate_human":
        metrics_inc("agent_message.escalations")
        enforce = bool(s.kai_chatwoot_enforce_live_handover)
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
        cw_live = extract_chatwoot_conversation_id(data)
        start_human_segment(user_id, cw_live or None)
        append_human_segment_turn(user_id, "user", text)
        append_human_segment_turn(user_id, "assistant", result.answer)
        freeze(user_id, True)
        payload = {
            "type": "handover",
            "message": kai_service.finalize_reply(user_id, result.answer, lang, suppress=True),
            "next_state": "human",
            "handover_applied": True,
        }
    else:
        suppress_footer = result.decision in ("direct_answer", "clarifying_question")
        payload = {
            "type": "reply",
            "message": kai_service.finalize_reply(user_id, result.answer, lang, suppress=suppress_footer),
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
async def agent_message(request: Request, x_admin_token: str | None = Header(default=None)):
    try:
        data = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="invalid_json") from exc
    try:
        return _process_agent_message_data(data, x_admin_token=x_admin_token)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/v2/agent/message")
async def agent_message_v2(request: Request, x_admin_token: str | None = Header(default=None)):
    try:
        data = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="invalid_json") from exc
    try:
        return _process_agent_message_data(data, x_admin_token=x_admin_token)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


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


@router.get("/admin/tech-backlog/tabs")
def admin_tech_backlog_tabs(x_admin_token: str | None = Header(default=None)):
    from kai.support_runtime.tech_backlog import list_backlog_sheet_tabs

    _require_admin(x_admin_token)
    return {"ok": True, "tabs": list_backlog_sheet_tabs()}
