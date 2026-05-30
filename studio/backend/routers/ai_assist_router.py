"""AI Assist — scoped DeepSeek chat that can read and patch tenant config files + plugin scripts."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Generator

import requests
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ai_assist_core import (
    SYSTEM_PROMPT,
    _record_usage_from_response,
    apply_patches,
    build_context,
    extract_patch,
    make_deepseek_client,
    preview_patches,
    validate_ai_assist_patches,
)
from database import get_db
from deps import get_current_user
from models import User
from routers.tenants_router import _assert_tenant_member
from tenant_compile import patch_list_touches_faq, run_tenant_compile

log = logging.getLogger("kai.ai_assist")

router = APIRouter(prefix="/tenants", tags=["ai-assist"])


@router.post("/{tenant_id}/ai-assist/chat")
def ai_assist_chat(
    tenant_id: str,
    body: dict,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    t = _assert_tenant_member(tenant_id, user, db)
    home = Path(t.workspace_home).resolve()

    messages: list[dict] = body.get("messages") or []
    apply: bool = bool(body.get("apply_patches", False))

    if apply:
        last_assistant = next(
            (m["content"] for m in reversed(messages) if m.get("role") == "assistant"),
            None,
        )
        if last_assistant:
            patch_block = extract_patch(last_assistant)
            if patch_block and patch_block.get("patches"):
                validate_ai_assist_patches(patch_block["patches"])
                applied = apply_patches(home, patch_block["patches"])
                payload: dict[str, Any] = {
                    "ok": True,
                    "applied": applied,
                    "summary": patch_block.get("summary", ""),
                }
                if patch_list_touches_faq(applied):
                    payload["compile"] = run_tenant_compile(home).model_dump()
                return payload
        return {"ok": False, "error": "No patch found in last assistant message"}

    api_key, base_url, model = make_deepseek_client()
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="AI Assist unavailable: DEEPSEEK_API_KEY not configured.",
        )

    sys_msg = SYSTEM_PROMPT + f"\n\n---\n\n{build_context(home)}"
    full_messages = [{"role": "system", "content": sys_msg}, *messages]
    tenant_slug = t.slug

    def _stream() -> Generator[str, None, None]:
        try:
            resp = requests.post(
                f"{base_url}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "model": model,
                    "messages": full_messages,
                    "temperature": 0.3,
                    "max_tokens": 3000,
                    "stream": True,
                    "stream_options": {"include_usage": True},
                },
                stream=True,
                timeout=90,
            )
            if not resp.ok:
                yield f"data: {json.dumps({'type': 'error', 'content': f'LLM error {resp.status_code}'})}\n\n"
                return

            full_text = ""
            for raw_line in resp.iter_lines():
                if not raw_line:
                    continue
                line = raw_line.decode("utf-8") if isinstance(raw_line, bytes) else raw_line
                if line.startswith("data: "):
                    payload = line[6:]
                    if payload.strip() == "[DONE]":
                        break
                    try:
                        chunk = json.loads(payload)
                        if chunk.get("usage"):
                            _record_usage_from_response(
                                chunk,
                                model=model,
                                tenant_slug=tenant_slug,
                                source="studio_ai_assist",
                            )
                        delta = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                        if delta:
                            full_text += delta
                            yield f"data: {json.dumps({'type': 'delta', 'content': delta})}\n\n"
                    except Exception:
                        continue

            patch_block = extract_patch(full_text)
            patches_preview: list[dict[str, str]] = []
            patch_error = ""
            if patch_block and patch_block.get("patches"):
                try:
                    validate_ai_assist_patches(patch_block["patches"])
                    patches_preview = preview_patches(home, patch_block["patches"])
                except HTTPException as exc:
                    patch_error = str(exc.detail)

            summary = patch_block.get("summary", "") if patch_block else ""
            if patch_error:
                summary = (summary + " " if summary else "") + f"[Patch rejected: {patch_error}]"
            yield f"data: {json.dumps({'type': 'done', 'patches': patches_preview, 'summary': summary})}\n\n"
        except Exception as exc:
            log.exception("AI assist stream error")
            yield f"data: {json.dumps({'type': 'error', 'content': str(exc)})}\n\n"

    return StreamingResponse(
        _stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
