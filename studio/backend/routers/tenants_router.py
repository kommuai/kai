"""Tenant CRUD + file-editing endpoints."""
from __future__ import annotations

import os
import re
import subprocess
import uuid
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_

from database import get_db
from deps import get_current_user
from models import Tenant, TenantInvite, TenantMembership, User
from schemas import CompileResult, FileContent, FileContentOut, InviteAccept, InviteCreate, InviteOut, TenantCreate, TenantOut
from kai_paths import kai_repo_root, kai_tenants_root

router = APIRouter(prefix="/tenants", tags=["tenants"])

KAI_TENANTS_ROOT = kai_tenants_root()
KAI_REPO = kai_repo_root()
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

_EDITABLE_FILES = {
    "workspace": "workspace.yaml",
    "system_prompt": "system_prompt.md",
    "faq": "knowledge/master_faq.md",
}


def _tenant_home(slug: str) -> Path:
    return KAI_TENANTS_ROOT / f"kai-tenant-{slug}"


def _assert_tenant_member(tenant_id: str, user: User, db: Session) -> Tenant:
    m = (
        db.query(TenantMembership)
        .filter(and_(TenantMembership.tenant_id == tenant_id, TenantMembership.user_id == user.id))
        .first()
    )
    if not m:
        raise HTTPException(status_code=404, detail="Tenant not found")
    t = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return t


def _assert_tenant_member_by_slug(slug: str, user: User, db: Session) -> Tenant:
    t = db.query(Tenant).filter(Tenant.slug == slug).first()
    if not t:
        raise HTTPException(status_code=404, detail="Tenant not found")
    _assert_tenant_member(t.id, user, db)
    return t


# ── List ──────────────────────────────────────────────────────────────────────

@router.get("", response_model=list[TenantOut])
def list_tenants(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return (
        db.query(Tenant)
        .join(TenantMembership, TenantMembership.tenant_id == Tenant.id)
        .filter(TenantMembership.user_id == user.id)
        .order_by(Tenant.created_at)
        .all()
    )


# ── Create ────────────────────────────────────────────────────────────────────

@router.post("", response_model=TenantOut, status_code=status.HTTP_201_CREATED)
def create_tenant(body: TenantCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if db.query(Tenant).filter(Tenant.slug == body.slug).first():
        raise HTTPException(status_code=400, detail="Slug already taken")

    home = _tenant_home(body.slug)
    if home.exists():
        raise HTTPException(status_code=409, detail=f"Directory already exists: {home}")

    # Scaffold from kai template
    (home / "knowledge").mkdir(parents=True, exist_ok=True)
    (home / "compiled").mkdir(parents=True, exist_ok=True)
    (home / "data").mkdir(parents=True, exist_ok=True)
    (home / "tools" / "plugins").mkdir(parents=True, exist_ok=True)

    workspace_content = _default_workspace(body.slug, body.display_name)
    (home / "workspace.yaml").write_text(workspace_content, encoding="utf-8")

    system_prompt_content = _default_system_prompt(body.display_name)
    (home / "system_prompt.md").write_text(system_prompt_content, encoding="utf-8")

    faq_content = _default_faq(body.display_name)
    (home / "knowledge" / "master_faq.md").write_text(faq_content, encoding="utf-8")

    tenant = Tenant(
        id=str(uuid.uuid4()),
        owner_id=user.id,
        slug=body.slug,
        display_name=body.display_name,
        description=body.description or "",
        workspace_home=str(home),
    )
    db.add(tenant)
    db.add(
        TenantMembership(
            id=str(uuid.uuid4()),
            tenant_id=tenant.id,
            user_id=user.id,
            role="member",
        )
    )
    db.commit()
    db.refresh(tenant)
    return tenant


# ── Get ───────────────────────────────────────────────────────────────────────

@router.get("/by-slug/{slug}", response_model=TenantOut)
def get_tenant_by_slug(slug: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _assert_tenant_member_by_slug(slug, user, db)


@router.get("/{tenant_id}", response_model=TenantOut)
def get_tenant(tenant_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _assert_tenant_member(tenant_id, user, db)


# ── File read/write ───────────────────────────────────────────────────────────

@router.get("/{tenant_id}/files/{file_key}", response_model=FileContentOut)
def get_file(tenant_id: str, file_key: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    t = _assert_tenant_member(tenant_id, user, db)
    rel = _EDITABLE_FILES.get(file_key)
    if not rel:
        raise HTTPException(status_code=400, detail=f"Unknown file key. Valid: {list(_EDITABLE_FILES)}")
    path = Path(t.workspace_home) / rel
    if not path.exists():
        return FileContentOut(path=rel, content="")
    return FileContentOut(path=rel, content=path.read_text(encoding="utf-8"))


@router.put("/{tenant_id}/files/{file_key}", response_model=FileContentOut)
def put_file(
    tenant_id: str,
    file_key: str,
    body: FileContent,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    t = _assert_tenant_member(tenant_id, user, db)
    rel = _EDITABLE_FILES.get(file_key)
    if not rel:
        raise HTTPException(status_code=400, detail=f"Unknown file key. Valid: {list(_EDITABLE_FILES)}")
    path = Path(t.workspace_home) / rel
    path.parent.mkdir(parents=True, exist_ok=True)

    if file_key == "workspace":
        try:
            yaml.safe_load(body.content)
        except yaml.YAMLError as exc:
            raise HTTPException(status_code=422, detail=f"Invalid YAML: {exc}")

    path.write_text(body.content, encoding="utf-8")
    return FileContentOut(path=rel, content=body.content)


# ── Compile ───────────────────────────────────────────────────────────────────

@router.post("/{tenant_id}/compile", response_model=CompileResult)
def compile_tenant(tenant_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    t = _assert_tenant_member(tenant_id, user, db)
    try:
        result = subprocess.run(
            ["python", "-m", "kai.cli", "compile"],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(KAI_REPO),
            env={**os.environ, "KAI_HOME": t.workspace_home},
        )
        if result.returncode != 0:
            return CompileResult(ok=False, message=result.stderr or result.stdout)
        # Parse "Compiled intents=N chunks=M" from output
        m = re.search(r"intents=(\d+)", result.stdout)
        intents = int(m.group(1)) if m else None
        return CompileResult(ok=True, message=result.stdout.strip(), intents=intents)
    except subprocess.TimeoutExpired:
        return CompileResult(ok=False, message="Compile timed out")
    except Exception as exc:
        return CompileResult(ok=False, message=str(exc))


# ── Invites ───────────────────────────────────────────────────────────────────

@router.get("/{tenant_id}/invites", response_model=list[InviteOut])
def list_invites(tenant_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _assert_tenant_member(tenant_id, user, db)
    invites = (
        db.query(TenantInvite)
        .filter(TenantInvite.tenant_id == tenant_id)
        .order_by(TenantInvite.created_at.desc())
        .all()
    )
    out: list[InviteOut] = []
    for inv in invites:
        item = InviteOut.model_validate(inv)
        item.invite_url = f"{FRONTEND_URL}/invite/{inv.token}"
        out.append(item)
    return out


@router.post("/{tenant_id}/invites", response_model=InviteOut, status_code=status.HTTP_201_CREATED)
def create_invite(
    tenant_id: str,
    body: InviteCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _assert_tenant_member(tenant_id, user, db)
    token = secrets.token_urlsafe(24)
    inv = TenantInvite(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        email=str(body.email).lower(),
        token=token,
        status="pending",
        created_by_user_id=user.id,
        created_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    db.add(inv)
    db.commit()
    db.refresh(inv)
    out = InviteOut.model_validate(inv)
    out.invite_url = f"{FRONTEND_URL}/invite/{inv.token}"
    return out


@router.post("/invites/accept", response_model=TenantOut)
def accept_invite(body: InviteAccept, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    inv = db.query(TenantInvite).filter(TenantInvite.token == body.token).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Invite not found")
    if inv.status != "pending":
        raise HTTPException(status_code=400, detail=f"Invite is {inv.status}")
    if inv.expires_at:
        exp = inv.expires_at
        # SQLite can return naive datetimes even when stored with tz. Normalize to UTC-aware.
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if exp < datetime.now(timezone.utc):
            inv.status = "expired"
            db.commit()
            raise HTTPException(status_code=400, detail="Invite expired")
    if inv.email.lower() != user.email.lower():
        raise HTTPException(status_code=403, detail="Invite email does not match your account")

    # Add membership (idempotent)
    existing = (
        db.query(TenantMembership)
        .filter(and_(TenantMembership.tenant_id == inv.tenant_id, TenantMembership.user_id == user.id))
        .first()
    )
    if not existing:
        db.add(
            TenantMembership(
                id=str(uuid.uuid4()),
                tenant_id=inv.tenant_id,
                user_id=user.id,
                role="member",
            )
        )

    inv.status = "accepted"
    db.commit()
    t = db.query(Tenant).filter(Tenant.id == inv.tenant_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return t


@router.delete("/{tenant_id}/invites/{invite_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_invite(tenant_id: str, invite_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _assert_tenant_member(tenant_id, user, db)
    inv = db.query(TenantInvite).filter(TenantInvite.id == invite_id, TenantInvite.tenant_id == tenant_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Invite not found")
    inv.status = "revoked"
    db.commit()
    return None


# ── Scaffold helpers ──────────────────────────────────────────────────────────

def _default_workspace(slug: str, name: str) -> str:
    return f"""version: '2'
tenant:
  id: {slug}
  display_name: {name}
  default_lang: en
  timezone: Asia/Kuala_Lumpur
paths:
  system_prompt: system_prompt.md
  knowledge_primary: knowledge/master_faq.md
  knowledge_compiled_dir: compiled
  knowledge_learn_queue: knowledge/learn_queue
  tools_plugins_dir: tools/plugins
knowledge:
  format: master_faq_v1
  compile: kb_chunks.jsonl
  inject_mode: full_context
  faq_preamble: |
    ## Authoritative FAQ

    This is the only source of truth for {name} answers. Use tools when the FAQ does not cover the request.
tools:
  enabled: []
channels:
  office:
    timezone: Asia/Kuala_Lumpur
    weekdays: [0, 1, 2, 3, 4]
    start_hour: 10
    end_hour: 18
  handover:
    dropoff_keyword: DROPOFF
    live_agent_keywords: [LA]
    resume_keywords: [resume, unfreeze, sambung]
  frozen:
    idle_hours: 24
  media:
    blocked_types: [image, video, audio, voice]
  fallbacks:
    no_signal_en: What do you need help with?
    post_tool_en: Can you share more detail?
  whatsapp:
    max_reply_chars: 4096
admin:
  whitelist_numbers: []
  learning:
    enabled: true
    min_confidence: 0.6
    max_items: 10
sop_sync:
  enabled: false
session_store:
  backend: sqlite
  path: data/sessions.db
session:
  idle_hours: 24
  max_history_messages: 100
agent:
  max_steps: 8
  footer_history_threshold: 10
compile:
  extra_artifacts: false
copy:
  keywords:
    dropoff: DROPOFF
    live_agent: [LA]
  footer:
    en: |


      For Live Agent, type LA
    history_threshold: 10
  after_hours:
    en: |


      PS: We're outside office hours. A live agent will follow up later.
  handover:
    dropoff_en: Please share the details. Type *resume* to continue with the bot.
    live_agent_en: A live agent will assist you soon. Type *resume* to continue with the bot.
  resume:
    en: Bot resumed. How can I help?
  media_guard:
    en: Please describe your issue in text; media is not supported yet.
tools_profile:
  active_profile: minimal
  profiles:
    minimal:
    - search_faq
    - search_session_memory
    - escalate_to_human
  profile_overrides: {{}}
  tools: []
contexts: []
"""


def _default_system_prompt(name: str) -> str:
    return f"""
You are the AI support agent for **{name}**.

## Your personality
- Helpful, friendly, concise.
- Reply in the language the user used.
- If unsure, ask ONE clear clarifying question instead of guessing.

## Response format
Output ONLY a JSON object.

When answering:
{{"action":"final","answer":"...","decision":"direct_answer","confidence":0.85,"source_ids":["faq:topic"]}}

When asking a clarifying question:
{{"action":"final","decision":"clarifying_question","question":"What is your order number?","confidence":0.55}}

When escalating to human:
{{"action":"final","answer":"Type LA and our team will assist.","decision":"escalate_human","confidence":0.4}}
"""


def _default_faq(name: str) -> str:
    return f"""# {name.upper()} — MASTER FAQ

Last updated: (set this date when you edit)

## intent: greeting
aliases:
- hello
- hi
- hey
answer:
Hello! How can I help you today?

## intent: office_hours
aliases:
- office hours
- when are you open
- operating hours
answer:
Mon–Fri 10AM–6PM (Malaysia time). Type **LA** for a live agent.

## intent: about
aliases:
- what do you do
- tell me about yourselves
answer:
We are {name}. How can I help you today?
"""
