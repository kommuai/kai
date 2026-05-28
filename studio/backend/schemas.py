"""Pydantic schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, EmailStr, field_validator


# ── Auth ──────────────────────────────────────────────────────────────────────

class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    name: str

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserOut"


# ── User ──────────────────────────────────────────────────────────────────────

class UserOut(BaseModel):
    id: str
    email: str
    name: str
    avatar_url: str
    provider: str
    created_at: datetime

    class Config:
        from_attributes = True


# ── Tenant ────────────────────────────────────────────────────────────────────

class TenantCreate(BaseModel):
    display_name: str
    description: Optional[str] = ""
    slug: str
    personality: Optional[str] = "friendly"
    bot_name: Optional[str] = ""
    company_name: Optional[str] = ""
    product_summary: Optional[str] = ""
    scope_cannot_answer: list[str] = []
    escalation_rules: list[str] = []
    fallback_behavior: Optional[str] = "escalate_if_unsure"

    @field_validator("personality")
    @classmethod
    def personality_valid(cls, v: Optional[str]) -> str:
        vv = (v or "friendly").strip().lower()
        allowed = {
            "friendly",
            "professional",
            "empathetic",
            "direct",
            "playful",
            "premium",
        }
        if vv not in allowed:
            raise ValueError(f"Personality must be one of: {', '.join(sorted(allowed))}")
        return vv

    @field_validator(
        "bot_name",
        "company_name",
        "product_summary",
        "fallback_behavior",
    )
    @classmethod
    def trim_optional_text(cls, v: Optional[str]) -> str:
        return (v or "").strip()

    @field_validator("scope_cannot_answer", "escalation_rules")
    @classmethod
    def normalize_string_list(cls, v: list[str]) -> list[str]:
        out: list[str] = []
        for item in v or []:
            s = str(item or "").strip()
            if s:
                out.append(s)
        # stable unique preserve order
        seen: set[str] = set()
        uniq: list[str] = []
        for s in out:
            if s in seen:
                continue
            seen.add(s)
            uniq.append(s)
        return uniq

    @field_validator("fallback_behavior")
    @classmethod
    def fallback_behavior_valid(cls, v: Optional[str]) -> str:
        vv = (v or "escalate_if_unsure").strip().lower()
        allowed = {
            "ask_one_question_then_escalate",
            "escalate_if_unsure",
            "say_not_confirmed_and_escalate",
            "best_effort_hallucination_risk",
        }
        if vv not in allowed:
            raise ValueError(f"Fallback behavior must be one of: {', '.join(sorted(allowed))}")
        return vv

    @field_validator("slug")
    @classmethod
    def slug_valid(cls, v: str) -> str:
        import re
        v = v.strip().lower()
        if not re.match(r"^[a-z0-9][a-z0-9-]{1,48}[a-z0-9]$", v):
            raise ValueError("Slug must be 3–50 lowercase alphanumeric/hyphen chars")
        return v


class TenantOut(BaseModel):
    id: str
    owner_id: str
    slug: str
    display_name: str
    description: str
    workspace_home: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SkillCapabilityOut(BaseModel):
    id: str
    description: str
    enabled: bool = True
    source: str  # "profile" | "document"
    path: str | None = None
    builtin: str | None = None
    canonical_builtin: str | None = None
    plugin: str | None = None


class TenantCapabilitiesOut(BaseModel):
    active_profile: str
    skills: list[SkillCapabilityOut]

class SkillToggleIn(BaseModel):
    enabled: bool
    source: str  # "profile" | "document"
    path: str | None = None


# ── Invites ───────────────────────────────────────────────────────────────────

class InviteCreate(BaseModel):
    email: EmailStr


class InviteOut(BaseModel):
    id: str
    tenant_id: str
    email: EmailStr
    token: str
    status: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    invite_url: Optional[str] = None

    class Config:
        from_attributes = True


class InviteAccept(BaseModel):
    token: str


class InvitePreviewOut(BaseModel):
    email: EmailStr
    tenant_name: str
    tenant_slug: str
    status: str
    expired: bool = False


# ── Tenant files ──────────────────────────────────────────────────────────────

class FileContent(BaseModel):
    content: str


class FileContentOut(BaseModel):
    path: str
    content: str


class CompileResult(BaseModel):
    ok: bool
    message: str
    intents: Optional[int] = None


# ── Inbox / Contacts (Kai sessions.db read-only + contact_tags) ───────────────

class MessageOut(BaseModel):
    role: str
    text: str
    created_at: Optional[str] = None


class MemoryFactOut(BaseModel):
    fact_type: str
    fact_key: str
    fact_value: str
    last_seen_at: Optional[str] = None


class ConversationOut(BaseModel):
    user_id: str
    frozen: bool
    last_activity_at: Optional[str] = None
    last_message_preview: str
    message_count: int


class ConversationListOut(BaseModel):
    items: list[ConversationOut]
    total: int


class ConversationDetailOut(BaseModel):
    user_id: str
    frozen: bool
    last_activity_at: Optional[str] = None
    messages: list[MessageOut]
    facts: list[MemoryFactOut]
    tags: list[str]
    chatwoot_conversation_id: Optional[str] = None


class ChatwootMetaOut(BaseModel):
    configured: bool
    conversation_id: Optional[str] = None
    status: Optional[str] = None
    labels: list[str] = []


class ChatwootStatusBody(BaseModel):
    status: str
    snoozed_until: Optional[int] = None

    @field_validator("status")
    @classmethod
    def status_ok(cls, v: str) -> str:
        s = (v or "").strip().lower()
        if s not in ("open", "resolved", "pending", "snoozed"):
            raise ValueError("status must be open, resolved, pending, or snoozed")
        return s


class ChatwootPrivateNoteBody(BaseModel):
    text: str

    @field_validator("text")
    @classmethod
    def note_nonempty(cls, v: str) -> str:
        t = (v or "").strip()
        if len(t) < 1:
            raise ValueError("Note cannot be empty")
        if len(t) > 8000:
            raise ValueError("Note too long")
        return t


class ChatwootLabelsBody(BaseModel):
    labels: list[str]


class ChatwootAccountLabelsOut(BaseModel):
    items: list[dict[str, Any]]


class SearchHitOut(BaseModel):
    user_id: str
    message_id: int
    role: str
    snippet: str
    created_at: str


class SearchResultsOut(BaseModel):
    query: str
    items: list[SearchHitOut]


class ContactOut(BaseModel):
    user_id: str
    display_name: str
    last_activity_at: Optional[str] = None
    frozen: bool = False
    tags: list[str] = []
    fact_preview: str = ""


class ContactListOut(BaseModel):
    items: list[ContactOut]
    total: int


class ContactDetailOut(BaseModel):
    user_id: str
    display_name: str
    frozen: bool = False
    last_activity_at: Optional[str] = None
    facts: list[MemoryFactOut]
    tags: list[str]


class TagCreate(BaseModel):
    tag: str

    @field_validator("tag")
    @classmethod
    def tag_valid(cls, v: str) -> str:
        import re

        t = (v or "").strip().lower()
        t = re.sub(r"[^a-z0-9-]+", "-", t).strip("-")
        if len(t) < 1 or len(t) > 32:
            raise ValueError("Tag must be 1–32 chars (letters, digits, hyphen)")
        return t


class ReplyCreate(BaseModel):
    text: str

    @field_validator("text")
    @classmethod
    def text_valid(cls, v: str) -> str:
        t = (v or "").strip()
        if len(t) < 1:
            raise ValueError("Message cannot be empty")
        if len(t) > 4096:
            raise ValueError("Message too long (max 4096 characters)")
        return t


class ReplyOut(BaseModel):
    ok: bool
    message: MessageOut
    chatwoot_delivered: bool = False
    chatwoot_error: Optional[str] = None
    chatwoot_conversation_id: Optional[str] = None
