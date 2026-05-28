"""Tenant CRUD + file-editing endpoints."""
from __future__ import annotations

import os
import re
import shutil
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
from schemas import (
    CompileResult,
    FileContent,
    FileContentOut,
    InviteAccept,
    InviteCreate,
    InviteOut,
    InvitePreviewOut,
    TenantCapabilitiesOut,
    TenantCreate,
    TenantOut,
)
from kai_paths import kai_repo_root, kai_tenants_root
from kai_capabilities import get_capabilities
from invite_service import _invite_expired, redeem_invite_token

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


def _assert_tenant_owner(tenant_id: str, user: User, db: Session) -> Tenant:
    t = _assert_tenant_member(tenant_id, user, db)
    if t.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Only the tenant owner can delete this tenant.")
    return t


def _safe_remove_workspace(slug: str, workspace_home: str) -> None:
    """Remove tenant directory only when it matches the expected path under KAI_TENANTS_ROOT."""
    root = KAI_TENANTS_ROOT.resolve()
    expected = _tenant_home(slug).resolve()
    home = Path(workspace_home).resolve()
    if home != expected:
        raise HTTPException(
            status_code=400,
            detail="Workspace path does not match the standard tenant folder; remove files manually.",
        )
    try:
        home.relative_to(root)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Workspace is outside the tenants root; remove files manually.",
        )
    if home.is_dir():
        shutil.rmtree(home)


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

    system_prompt_content = _default_system_prompt(
        body.display_name,
        body.personality or "friendly",
        bot_name=body.bot_name,
        company_name=body.company_name,
        product_summary=body.product_summary,
        scope_cannot_answer=body.scope_cannot_answer,
        escalation_rules=body.escalation_rules,
        fallback_behavior=body.fallback_behavior,
    )
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


@router.delete("/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tenant(
    tenant_id: str,
    delete_workspace: bool = False,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Remove tenant from Studio. Optionally delete the workspace folder on disk (owner only)."""
    t = _assert_tenant_owner(tenant_id, user, db)
    slug = t.slug
    workspace_home = t.workspace_home

    db.delete(t)
    db.commit()

    if delete_workspace:
        _safe_remove_workspace(slug, workspace_home)

    return None


@router.get("/{tenant_id}/capabilities", response_model=TenantCapabilitiesOut)
def tenant_capabilities(tenant_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    t = _assert_tenant_member(tenant_id, user, db)
    try:
        data = get_capabilities(t.workspace_home)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Could not load capabilities: {exc}") from exc
    return TenantCapabilitiesOut.model_validate(data)


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


@router.get("/invites/{token}", response_model=InvitePreviewOut)
def invite_preview(token: str, db: Session = Depends(get_db)):
    inv = db.query(TenantInvite).filter(TenantInvite.token == token).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Invite not found")
    t = db.query(Tenant).filter(Tenant.id == inv.tenant_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Tenant not found")
    expired = inv.status == "expired" or (inv.status == "pending" and _invite_expired(inv))
    return InvitePreviewOut(
        email=inv.email,
        tenant_name=t.display_name,
        tenant_slug=t.slug,
        status=inv.status,
        expired=expired,
    )


@router.post("/invites/accept", response_model=TenantOut)
def accept_invite(body: InviteAccept, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return redeem_invite_token(db, user, body.token)


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
    dropoff_en: Please share the details. Type *resume* to continue with the AI support agent.
    live_agent_en: A live agent will assist you soon. Type *resume* to continue with the AI support agent.
  resume:
    en: AI support agent resumed. How can I help?
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


def _default_system_prompt(
    name: str,
    personality: str,
    *,
    bot_name: str = "",
    company_name: str = "",
    product_summary: str = "",
    scope_cannot_answer: list[str] | str = "",
    escalation_rules: list[str] | str = "",
    fallback_behavior: str = "",
) -> str:
    personality = (personality or "friendly").strip().lower()
    blocks: dict[str, str] = {
        "friendly": """## Your personality
- Warm, helpful, and concise.
- Reply in the language the user used.
- Ask ONE clear clarifying question if information is missing.""",
        "professional": """## Your personality
- Professional, structured, and calm.
- Use short headings or bullet points when useful.
- Confirm key details (order number, date, model) before taking action.""",
        "empathetic": """## Your personality
- Empathetic and reassuring; acknowledge frustration when appropriate.
- Keep answers short and actionable.
- Use gentle language; avoid sounding robotic or blaming the user.""",
        "direct": """## Your personality
- Direct and efficient.
- Prioritize the fastest path to resolution.
- Ask only the minimum questions needed; no extra fluff.""",
        "playful": """## Your personality
- Light, upbeat, and friendly (no jokes when user is upset).
- Keep it short; make the interaction feel human.
- Still prioritize correctness over humor.""",
        "premium": """## Your personality
- Premium concierge tone: confident, polished, and proactive.
- Offer next steps and options.
- Avoid casual slang; be crisp and high-trust.""",
    }
    persona_block = blocks.get(personality, blocks["friendly"])
    bot = (bot_name or "").strip() or "Kai"
    company = (company_name or "").strip() or name
    product = (product_summary or "").strip()
    cannot_answer_list = scope_cannot_answer if isinstance(scope_cannot_answer, list) else []
    cannot_answer_text = (scope_cannot_answer or "").strip() if isinstance(scope_cannot_answer, str) else ""
    escalation_list = escalation_rules if isinstance(escalation_rules, list) else []
    escalation_text = (escalation_rules or "").strip() if isinstance(escalation_rules, str) else ""

    def _bullets(items: list[str]) -> str:
        cleaned = [str(x).strip() for x in items if str(x).strip()]
        if not cleaned:
            return ""
        return "\n".join([f"- {x}" for x in cleaned])

    cannot_answer = _bullets(cannot_answer_list) or cannot_answer_text
    escalation = _bullets(escalation_list) or escalation_text

    fb = (fallback_behavior or "").strip().lower()
    fallback_map = {
        "ask_one_question_then_escalate": "If you are unsure, ask ONE clear clarifying question. If still unsure, escalate to a human.",
        "escalate_if_unsure": "If you are unsure, do not guess. Escalate to a human for verification.",
        "say_not_confirmed_and_escalate": "If you are unsure, say the information is not confirmed, then escalate to a human for verification.",
        "best_effort_hallucination_risk": "Try your best to answer even if it may not be confirmed. State uncertainty clearly and warn there is a hallucination risk. Offer to escalate to a human for verification.",
    }
    fallback = fallback_map.get(fb, fallback_map["escalate_if_unsure"])

    def _section(title: str, body: str) -> str:
        b = (body or "").strip()
        if not b:
            return ""
        return f"## {title}\n{b}\n"

    return f"""
## Role and identity
You are **{bot}**, the official customer support assistant for **{company}**.

{_section("Business context", product)}
{_section("Scope — what you must not answer", cannot_answer)}
## Source of truth
Use **master_faq.md** as the source of truth. If the answer is not confirmed in **master_faq.md**, do not guess—escalate to a human.

{_section("Escalation rules", escalation)}
{_section("Fallback behavior", fallback)}

{persona_block}

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
