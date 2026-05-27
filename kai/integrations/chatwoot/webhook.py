from __future__ import annotations

import hmac
import logging
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request

from kai.api.v2.agent_message import _process_agent_message_data
from kai.engine.metrics import inc
from kai.integrations.chatwoot.client import ChatwootClient
from kai.integrations.chatwoot.idempotency import try_mark_processed
from kai.integrations.chatwoot.mapper import map_chatwoot_event_to_agent_data, should_skip_event
from kai.services.chatwoot_handover import extract_chatwoot_conversation_id
from kai.settings import get_settings

log = logging.getLogger("kai.chatwoot.webhook")
router = APIRouter(tags=["chatwoot"])

_REPLY_TYPES = frozenset({"reply", "handover", "handover_failed"})


def _verify_webhook_secret(
    secret: str,
    *,
    header_token: str | None,
    query_token: str | None,
) -> None:
    expected = secret.strip()
    if not expected:
        return
    provided = (header_token or query_token or "").strip()
    if not provided or not hmac.compare_digest(provided, expected):
        raise HTTPException(status_code=401, detail="invalid_webhook_token")


def _post_reply_if_needed(out: dict[str, Any], agent_data: dict[str, Any]) -> None:
    msg_type = str(out.get("type") or "")
    if msg_type not in _REPLY_TYPES:
        return
    text = (out.get("message") or "").strip()
    if not text:
        return

    conv_id = extract_chatwoot_conversation_id(agent_data)
    if not conv_id:
        log.warning("Chatwoot reply skipped: no conversation_id trace=%s", out.get("trace_id"))
        inc("chatwoot.webhook.reply_skipped_no_conv")
        return

    client = ChatwootClient()
    ok, err = client.create_outgoing_message(conv_id, text)
    if ok:
        inc("chatwoot.webhook.replies_posted")
        log.info(
            "Chatwoot reply posted conv=%s type=%s trace=%s",
            conv_id,
            msg_type,
            out.get("trace_id"),
        )
    else:
        inc("chatwoot.webhook.reply_failed")
        log.error(
            "Chatwoot reply failed conv=%s err=%s trace=%s",
            conv_id,
            err,
            out.get("trace_id"),
        )


def _process_chatwoot_message(agent_data: dict[str, Any], message_id: str) -> None:
    try:
        out = _process_agent_message_data(agent_data)
    except Exception:
        inc("chatwoot.webhook.process_errors")
        log.exception("Chatwoot webhook process failed message_id=%s", message_id)
        return

    inc("chatwoot.webhook.processed")
    _post_reply_if_needed(out, agent_data)


@router.post("/webhooks/chatwoot")
async def chatwoot_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_chatwoot_bot_token: str | None = Header(default=None, alias="X-Chatwoot-Bot-Token"),
):
    s = get_settings()
    if not s.kai_chatwoot_bot_enabled:
        raise HTTPException(status_code=503, detail="chatwoot_bot_disabled")

    _verify_webhook_secret(
        s.kai_chatwoot_webhook_secret,
        header_token=x_chatwoot_bot_token,
        query_token=request.query_params.get("token"),
    )

    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="invalid_json") from exc

    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="payload_must_be_object")

    skip, reason = should_skip_event(payload, allowed_inbox_ids=s.kai_chatwoot_inbox_ids)
    if skip:
        inc("chatwoot.webhook.skipped")
        return {"ok": True, "skipped": reason}

    message = payload.get("message") if isinstance(payload.get("message"), dict) else payload
    message_id = str((message or {}).get("id") or payload.get("id") or "").strip()
    if message_id and not try_mark_processed(message_id):
        inc("chatwoot.webhook.duplicate")
        return {"ok": True, "skipped": "duplicate"}

    agent_data = map_chatwoot_event_to_agent_data(payload)
    if not agent_data:
        return {"ok": True, "skipped": "unmapable"}

    if message_id:
        agent_data.setdefault("chatwoot_message_id", message_id)

    background_tasks.add_task(_process_chatwoot_message, agent_data, message_id)
    return {"ok": True, "accepted": True}
