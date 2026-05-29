"""New-tenant onboarding: staged document upload + AI bootstrap."""
from __future__ import annotations

import json
import re
import shutil
import uuid
from pathlib import Path
from typing import Any, Generator

from fastapi import HTTPException, UploadFile

from ai_assist_core import (
    BOOTSTRAP_SYSTEM_PROMPT,
    apply_patches,
    build_context,
    chat_completion,
    extract_patch,
)
from kai_paths import kai_tenants_root

ONBOARDING_ROOT = kai_tenants_root() / ".studio-onboarding"
MAX_FILES = 20
MAX_FILE_BYTES = 10 * 1024 * 1024   # 10 MB (raised for PDFs)
MAX_SESSION_BYTES = 50 * 1024 * 1024
ALLOWED_SUFFIXES = {".txt", ".md", ".markdown", ".csv", ".json", ".yaml", ".yml", ".html", ".htm", ".pdf"}
_TEXT_SUFFIXES = ALLOWED_SUFFIXES - {".pdf"}


def _session_dir(user_id: str, session_id: str) -> Path:
    safe_sid = re.sub(r"[^a-zA-Z0-9_-]", "", session_id)
    if not safe_sid or safe_sid != session_id:
        raise HTTPException(status_code=400, detail="Invalid session id")
    return ONBOARDING_ROOT / user_id / safe_sid


def create_session(user_id: str) -> str:
    session_id = uuid.uuid4().hex
    d = _session_dir(user_id, session_id)
    d.mkdir(parents=True, exist_ok=True)
    (d / ".meta.json").write_text(json.dumps({"user_id": user_id}), encoding="utf-8")
    return session_id


def _assert_session_owner(user_id: str, session_id: str) -> Path:
    d = _session_dir(user_id, session_id)
    if not d.is_dir():
        raise HTTPException(status_code=404, detail="Onboarding session not found")
    meta = d / ".meta.json"
    if meta.is_file():
        try:
            meta_user = json.loads(meta.read_text(encoding="utf-8")).get("user_id")
            if meta_user and meta_user != user_id:
                raise HTTPException(status_code=403, detail="Session access denied")
        except json.JSONDecodeError:
            pass
    return d


def list_documents(user_id: str, session_id: str) -> list[dict[str, Any]]:
    d = _assert_session_owner(user_id, session_id)
    out = []
    for f in sorted(d.iterdir()):
        if f.is_file() and not f.name.startswith("."):
            out.append({"name": f.name, "size": f.stat().st_size})
    return out


def _safe_filename(name: str) -> str:
    base = Path(name).name
    base = re.sub(r"[^\w.\- ]", "_", base).strip()
    if not base or base.startswith("."):
        raise HTTPException(status_code=400, detail=f"Invalid filename: {name}")
    return base[:200]


def _resolve_upload_filename(upload: UploadFile) -> str:
    """Browser may send empty name, 'blob', or extensionless files — normalize before save."""
    raw = (upload.filename or "").strip()
    if not raw and getattr(upload, "headers", None):
        cd = upload.headers.get("content-disposition") or ""
        if "filename=" in cd:
            part = cd.split("filename=", 1)[-1].strip().strip('"').strip("'")
            raw = part.split(";")[0].strip()
    name = Path(raw).name if raw else ""
    if not name or name.lower() == "blob":
        name = "upload.txt"
    if not Path(name).suffix:
        ctype = (upload.content_type or "").split(";")[0].strip().lower()
        ext = {
            "text/plain": ".txt",
            "text/markdown": ".md",
            "text/csv": ".csv",
            "application/pdf": ".pdf",
        }.get(ctype, ".txt")
        name = f"{name}{ext}"
    return _safe_filename(name)


async def upload_documents(user_id: str, session_id: str, files: list[UploadFile]) -> list[dict[str, Any]]:
    d = _assert_session_owner(user_id, session_id)
    existing = list_documents(user_id, session_id)
    if len(existing) + len(files) > MAX_FILES:
        raise HTTPException(status_code=400, detail=f"Maximum {MAX_FILES} files per session")

    total = sum(x["size"] for x in existing)
    saved: list[dict[str, Any]] = []

    for upload in files:
        fname = _resolve_upload_filename(upload)
        suffix = Path(fname).suffix.lower()
        if suffix not in ALLOWED_SUFFIXES:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {suffix}. Use {', '.join(sorted(ALLOWED_SUFFIXES))}",
            )
        data = await upload.read()
        if len(data) > MAX_FILE_BYTES:
            raise HTTPException(status_code=400, detail=f"{fname} exceeds {MAX_FILE_BYTES // (1024 * 1024)}MB limit")
        total += len(data)
        if total > MAX_SESSION_BYTES:
            raise HTTPException(status_code=400, detail="Total upload size limit exceeded")
        (d / fname).write_bytes(data)
        saved.append({"name": fname, "size": len(data)})

    if files and not saved:
        raise HTTPException(
            status_code=400,
            detail="Could not save uploaded file. Use a .txt, .md, .csv, or other supported type.",
        )

    return list_documents(user_id, session_id)


def move_onboarding_whatsapp_to_tenant(user_id: str, session_id: str, tenant_home: Path) -> str | None:
    """Copy baileys auth from onboarding session into tenant workspace; return linked phone."""
    import json
    import shutil

    session_base = _session_dir(user_id, session_id)
    src_auth = session_base / "whatsapp" / "baileys-auth"
    if not src_auth.is_dir() or not any(src_auth.iterdir()):
        return None
    meta_path = session_base / ".whatsapp-link.json"
    meta: dict = {}
    if meta_path.is_file():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8")) or {}
        except json.JSONDecodeError:
            meta = {}
    dest_auth = tenant_home / "data" / "whatsapp" / "baileys-auth"
    dest_auth.parent.mkdir(parents=True, exist_ok=True)
    if dest_auth.exists():
        shutil.rmtree(dest_auth, ignore_errors=True)
    shutil.copytree(src_auth, dest_auth)
    phone = (meta.get("phone") or "").strip() or None
    if not phone:
        from channel_config import phone_from_baileys_auth

        phone = phone_from_baileys_auth(tenant_home)
    link_id = meta.get("link_id")
    if link_id:
        from whatsapp_bridge_client import stop_link

        stop_link(str(link_id))
    return phone


def attach_session_to_tenant(user_id: str, session_id: str, tenant_home: Path) -> Path | None:
    """Copy staged files into tenant knowledge/onboarding_sources. Returns dest dir or None if empty."""
    d = _assert_session_owner(user_id, session_id)
    files = [f for f in d.iterdir() if f.is_file() and not f.name.startswith(".")]
    if not files:
        shutil.rmtree(d, ignore_errors=True)
        return None

    dest = tenant_home / "knowledge" / "onboarding_sources"
    dest.mkdir(parents=True, exist_ok=True)
    for f in files:
        shutil.copy2(f, dest / f.name)
    shutil.rmtree(d, ignore_errors=True)
    user_root = ONBOARDING_ROOT / user_id
    if user_root.is_dir() and not any(user_root.iterdir()):
        shutil.rmtree(user_root, ignore_errors=True)
    return dest


def _extract_pdf_text(path: Path) -> str:
    try:
        import pdfplumber
        with pdfplumber.open(str(path)) as pdf:
            parts = [page.extract_text() or "" for page in pdf.pages]
        return "\n\n".join(p for p in parts if p.strip())[:80000]
    except Exception as exc:
        return f"[PDF extract failed: {exc}]"


def _read_source_texts(sources_dir: Path) -> list[dict[str, str]]:
    docs: list[dict[str, str]] = []
    for f in sorted(sources_dir.iterdir()):
        if not f.is_file():
            continue
        suf = f.suffix.lower()
        if suf == ".pdf":
            text = _extract_pdf_text(f)
        elif suf in _TEXT_SUFFIXES:
            text = f.read_text(encoding="utf-8", errors="replace")
        else:
            continue
        if text.strip():
            docs.append({"name": f.name, "text": text[:80000]})
    return docs


def _format_questionnaire(q: dict[str, Any]) -> str:
    lines = [
        f"Company / display name: {q.get('display_name', '')}",
        f"Product summary: {q.get('product_summary', '') or q.get('description', '')}",
        f"AI agent name: {q.get('bot_name', '')}",
        f"Personality: {q.get('personality', 'friendly')}",
        f"Scope must NOT answer: {', '.join(q.get('scope_cannot_answer') or [])}",
        f"Escalation rules: {', '.join(q.get('escalation_rules') or [])}",
        f"Fallback behavior: {q.get('fallback_behavior', '')}",
    ]
    return "\n".join(lines)


def bootstrap_stream(
    tenant_home: Path,
    sources_dir: Path,
    questionnaire: dict[str, Any],
    *,
    tenant_slug: str | None = None,
) -> Generator[str, None, None]:
    def emit(obj: dict[str, Any]) -> str:
        return f"data: {json.dumps(obj)}\n\n"

    yield emit({"type": "progress", "stage": "reading", "percent": 15, "message": "Reading uploaded documents…"})

    docs = _read_source_texts(sources_dir)
    if not docs:
        yield emit({"type": "error", "message": "No readable text found in uploaded files."})
        return

    yield emit(
        {
            "type": "progress",
            "stage": "analyzing",
            "percent": 45,
            "message": f"Analyzing {len(docs)} document(s) with AI…",
        }
    )

    doc_block = "\n\n".join(
        f"### Document: {d['name']}\n```\n{d['text'][:12000]}\n```" for d in docs
    )
    user_msg = (
        f"## Questionnaire\n{_format_questionnaire(questionnaire)}\n\n"
        f"## Uploaded documents\n{doc_block}\n\n"
        f"## Current workspace (update as needed)\n{build_context(tenant_home)}\n\n"
        "Populate workspace.yaml, system_prompt.md, and master_faq.md from the documents and questionnaire. "
        "Output only the kai-patch block."
    )

    try:
        raw = chat_completion(
            BOOTSTRAP_SYSTEM_PROMPT,
            user_msg,
            max_tokens=8000,
            temperature=0.2,
            tenant_slug=tenant_slug,
            source="studio_onboarding",
        )
    except HTTPException as exc:
        yield emit({"type": "error", "message": str(exc.detail)})
        return
    except Exception as exc:
        yield emit({"type": "error", "message": str(exc)})
        return

    patch_block = extract_patch(raw)
    if not patch_block or not patch_block.get("patches"):
        yield emit({"type": "error", "message": "AI did not return a valid configuration patch."})
        return

    yield emit(
        {
            "type": "progress",
            "stage": "writing",
            "percent": 80,
            "message": "Writing configuration files…",
        }
    )

    try:
        applied = apply_patches(tenant_home, patch_block["patches"])
    except HTTPException as exc:
        yield emit({"type": "error", "message": str(exc.detail)})
        return

    from channel_config import reapply_saved_channel

    if reapply_saved_channel(tenant_home):
        yield emit(
            {
                "type": "progress",
                "stage": "channels",
                "percent": 92,
                "message": "Restored WhatsApp / channel settings…",
            }
        )

    done_payload: dict = {
        "type": "done",
        "percent": 100,
        "summary": patch_block.get("summary", "Configuration updated from your documents."),
        "applied": applied,
    }
    from tenant_compile import patch_list_touches_faq, run_tenant_compile

    if patch_list_touches_faq(applied):
        done_payload["compile"] = run_tenant_compile(tenant_home).model_dump()
    yield emit(done_payload)
