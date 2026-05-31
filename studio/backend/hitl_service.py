"""HITL knowledge-base patch proposal via AI Assist."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import requests
from fastapi import HTTPException

from ai_assist_core import (
    SYSTEM_PROMPT,
    apply_patches,
    build_context,
    extract_patch,
    make_deepseek_client,
    preview_patches,
    validate_ai_assist_patches,
)
from tenant_compile import patch_list_touches_faq, run_tenant_compile

log = logging.getLogger("shadou.hitl_service")

HITL_KB_USER_PROMPT = """A live support turn needs a knowledge-base update after human review.

Customer question:
{question}

Bot answer (low confidence — do NOT reuse verbatim unless correct):
{bot_answer}

Operator verified reply sent to the customer:
{operator_reply}

Task: add or update ONE FAQ intent in master_faq.md so similar future questions are answered from the knowledge base.

Rules:
- Output ONLY a ```shadou-patch``` JSON block (faq_intent patch type only).
- intent_id: short snake_case slug derived from the topic.
- Include aliases the customer might use and the operator reply as the canonical answer.
- Do not change workspace.yaml or system_prompt.md.
"""


def propose_kb_patch(home: Path, ticket: dict[str, Any], *, tenant_slug: str = "") -> dict[str, Any]:
    operator_reply = (ticket.get("operator_reply") or "").strip()
    if not operator_reply:
        raise HTTPException(status_code=400, detail="Send a customer reply before proposing a KB update")

    api_key, base_url, model = make_deepseek_client()
    if not api_key:
        raise HTTPException(status_code=503, detail="AI Assist unavailable: DEEPSEEK_API_KEY not configured")

    user_content = HITL_KB_USER_PROMPT.format(
        question=ticket.get("user_question") or "",
        bot_answer=ticket.get("bot_answer") or "",
        operator_reply=operator_reply,
    )
    sys_msg = SYSTEM_PROMPT + f"\n\n---\n\n{build_context(home)}"
    messages = [
        {"role": "system", "content": sys_msg},
        {"role": "user", "content": user_content},
    ]

    try:
        resp = requests.post(
            f"{base_url}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": model, "messages": messages, "temperature": 0.2, "max_tokens": 2500},
            timeout=90,
        )
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"LLM request failed: {exc}") from exc

    if not resp.ok:
        raise HTTPException(status_code=502, detail=f"LLM error {resp.status_code}")

    full_text = resp.json().get("choices", [{}])[0].get("message", {}).get("content", "") or ""
    patch_block = extract_patch(full_text)
    if not patch_block or not patch_block.get("patches"):
        raise HTTPException(status_code=422, detail="AI did not produce a valid shadou-patch block")

    validate_ai_assist_patches(patch_block["patches"])
    patches_preview = preview_patches(home, patch_block["patches"])

    return {
        "assistant_message": full_text,
        "patches": patches_preview,
        "summary": patch_block.get("summary", ""),
        "patch_block": patch_block,
    }


def apply_kb_patch(home: Path, assistant_message: str) -> dict[str, Any]:
    patch_block = extract_patch(assistant_message)
    if not patch_block or not patch_block.get("patches"):
        raise HTTPException(status_code=422, detail="No patch found in assistant message")
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
