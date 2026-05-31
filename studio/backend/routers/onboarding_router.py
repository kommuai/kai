"""Onboarding document upload + AI bootstrap for new tenants."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from database import get_db
from deps import get_current_user
from models import User
from onboarding_service import (
    attach_session_to_tenant,
    bootstrap_stream,
    create_session,
    list_documents,
    upload_documents,
)
from routers.tenants_router import _assert_tenant_member

router = APIRouter(prefix="/tenants/onboarding", tags=["onboarding"])


@router.post("/sessions")
def new_onboarding_session(user: User = Depends(get_current_user)):
    session_id = create_session(user.id)
    return {"session_id": session_id}


@router.get("/sessions/{session_id}/documents")
def get_session_documents(session_id: str, user: User = Depends(get_current_user)):
    return {"documents": list_documents(user.id, session_id)}


@router.post("/sessions/{session_id}/documents")
async def post_session_documents(
    session_id: str,
    request: Request,
    user: User = Depends(get_current_user),
):
    """Accept any multipart file field (browser may name it 'file' or 'files')."""
    import logging
    log = logging.getLogger("shadou.upload")
    ct = request.headers.get("content-type", "")
    log.info("upload content-type: %s", ct)

    uploads: list[UploadFile] = []
    try:
        form = await request.form()
        for key, val in form.multi_items():
            log.info("form field: key=%r type=%s filename=%r", key, type(val).__name__, getattr(val, "filename", None))
            if hasattr(val, "read") and hasattr(val, "filename"):
                uploads.append(val)  # type: ignore[arg-type]
    except Exception as exc:
        log.error("form parse error: %s", exc)
        raise HTTPException(status_code=400, detail=f"Could not parse upload: {exc}")

    if not uploads:
        log.warning("no upload fields found in content-type=%s", ct)
        raise HTTPException(
            status_code=400,
            detail=f"No file received (content-type: {ct}). Try a .txt or .md file.",
        )

    docs = await upload_documents(user.id, session_id, uploads)
    if not docs:
        raise HTTPException(status_code=500, detail="File upload failed to persist on disk.")
    return {"documents": docs}


@router.post("/{tenant_id}/bootstrap")
def bootstrap_tenant_from_documents(
    tenant_id: str,
    body: dict[str, Any],
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    body: { questionnaire: {...} }
    Sources must already be in tenant knowledge/onboarding_sources (attached at create).
    Streams SSE progress events.
    """
    t = _assert_tenant_member(tenant_id, user, db)
    home = Path(t.workspace_home).resolve()
    sources = home / "knowledge" / "onboarding_sources"
    if not sources.is_dir() or not any(sources.iterdir()):
        return StreamingResponse(
            iter([f"data: {json.dumps({'type': 'error', 'message': 'No onboarding documents found for this tenant.'})}\n\n"]),
            media_type="text/event-stream",
        )

    questionnaire = body.get("questionnaire") or {}

    return StreamingResponse(
        bootstrap_stream(home, sources, questionnaire, tenant_slug=t.slug),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
