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

from kai.lib.lang import resolve_lang
from kai.services.container import kai_service, support_runtime_service
from kai.support_runtime.gateway import run_support_turn

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
    msg_type = (data.get("type") or data.get("message_type") or "").strip().lower()
    if msg_type and ch.is_blocked_media_type(msg_type):
        start = time.time()
        lang_media = resolve_lang(user_id=str(data.get("phone_number") or "unknown"))
        payload = {
            "type": "reply",
            "message": ch.media_guard_en if lang_media == "EN" else ch.media_guard_bm,
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
    if data.get("media_url") and ch.blocked_media_types:
        start = time.time()
        lang_media = resolve_lang(user_id=str(data.get("phone_number") or "unknown"))
        payload = {
            "type": "reply",
            "message": ch.media_guard_en if lang_media == "EN" else ch.media_guard_bm,
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
    lang = resolve_lang(user_id=user_id, explicit=data.get("lang"))

    if not text:
        return _merge_trace({"ok": True}, trace_id=trace_id, mode=mode, capability_used="empty", start=start)

    metrics_inc("agent_message.requests")
    s = get_settings()

    try:
        from kai.workspace.admin_config import get_admin_config
        _admin_cfg = get_admin_config()
        _is_admin = _admin_cfg.is_admin(user_id)
    except Exception:
        _admin_cfg = None
        _is_admin = False

    try:
        outcome = run_support_turn(
            user_id=user_id,
            text=text,
            lang=lang,
            use_pre_router=True,
            apply_grounding=True,
        )
    except Exception:
        metrics_inc("agent_message.runtime_errors")
        log.exception("support_runtime gateway failed trace_id=%s user_id=%s", trace_id, user_id)
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

    if outcome.pre_router is not None and outcome.runtime is None:
        return _merge_trace(
            outcome.pre_router,
            trace_id=trace_id,
            mode=mode,
            capability_used="pre_router",
            start=start,
        )

    result = outcome.runtime
    if result is None:
        payload = {"type": outcome.kind, "message": outcome.message, "next_state": outcome.next_state}
        return _merge_trace(payload, trace_id=trace_id, mode=mode, capability_used="gateway", start=start)

    if (
        not _is_admin
        and _admin_cfg is not None
        and _admin_cfg.learning.enabled
        and result.confidence is not None
        and result.confidence < _admin_cfg.learning.min_confidence
    ):
        try:
            from kai.lib.learning_events import record_event
            record_event(
                user_id=user_id,
                user_text=text,
                decision=result.decision or "",
                confidence=float(result.confidence),
                fallback_reason=result.fallback_reason or "",
                trace_id=trace_id,
            )
        except Exception:
            pass

    debug_env = bool(s.kai_route_agent_debug_enabled)
    debug_requested = bool(data.get("debug_route_agent"))
    include_debug = debug_env and (debug_requested and _admin_token_valid(x_admin_token))

    if outcome.kind == "handover":
        metrics_inc("agent_message.escalations")
        payload = {
            "type": "handover",
            "message": outcome.message,
            "next_state": "human",
            "handover_applied": True,
        }
    else:
        payload = {
            "type": "reply",
            "message": outcome.message,
            "next_state": outcome.next_state,
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
