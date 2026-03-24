import logging
import time
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import PlainTextResponse

from core.policy.settings import RouteMode, get_route_mode, get_shadow_mode_enabled
from core.router.engine import RouterEngine
from core.skills.workspace_factory import build_workspace_skill, get_workspace_skill_registry
from lang_detect import is_malay
from services.container import kai_service

log = logging.getLogger("kai.v2")
router = APIRouter()


def _build_router(mode: RouteMode) -> RouterEngine:
    registry = get_workspace_skill_registry()
    skills = [build_workspace_skill(m) for m in registry.enabled_skills()]
    return RouterEngine(skills=skills, mode=mode)


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

    engine = _build_router(mode)
    result = engine.route_query(user_id=user_id, text=text, lang=lang)
    if result.ok:
        return _merge_trace(
            {
                "type": "reply",
                "message": kai_service.add_footer(user_id, result.answer, lang),
                "next_state": "bot",
            },
            trace_id=trace_id,
            mode=mode,
            capability_used=result.capability_used,
            start=start,
            fallback_reason=result.fallback_reason or "",
        )

    main_out = kai_service.main_conversation(data)
    return _merge_trace(
        main_out,
        trace_id=trace_id,
        mode=mode,
        capability_used="main_conversation",
        start=start,
        fallback_reason=result.fallback_reason or "no_skill_success",
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

    if get_shadow_mode_enabled():
        try:
            shadow = kai_service.handle_agent_message(data)
            log.info(
                "[Shadow] trace_id=%s mode=%s cap=%s v2_type=%s shadow_type=%s",
                out.get("trace_id"),
                get_route_mode().value,
                out.get("capability_used", ""),
                out.get("type", ""),
                shadow.get("type", ""),
            )
        except Exception as exc:  # noqa: BLE001
            log.warning("[Shadow] trace_id=%s err=%s", out.get("trace_id"), exc)
    return out


@router.post("/admin/reset_memory")
async def admin_reset_memory(request: Request):
    user_id = request.query_params.get("user_id") or (await request.form()).get("user_id")
    msg = kai_service.admin_reset_memory(user_id)
    return PlainTextResponse(msg)


@router.post("/admin/refresh-sop")
def refresh_sop_endpoint():
    return kai_service.refresh_sop_and_warranty()
