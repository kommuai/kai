"""Tenant invite redemption (token accept + pending-by-email)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import and_
from sqlalchemy.orm import Session

from models import Tenant, TenantInvite, TenantMembership, User


def _invite_expired(inv: TenantInvite) -> bool:
    if not inv.expires_at:
        return False
    exp = inv.expires_at
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    return exp < datetime.now(timezone.utc)


def _add_membership(db: Session, tenant_id: str, user_id: str) -> None:
    existing = (
        db.query(TenantMembership)
        .filter(and_(TenantMembership.tenant_id == tenant_id, TenantMembership.user_id == user_id))
        .first()
    )
    if not existing:
        db.add(
            TenantMembership(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                user_id=user_id,
                role="member",
            )
        )


def redeem_invite(db: Session, user: User, inv: TenantInvite) -> Tenant:
    if inv.status != "pending":
        raise HTTPException(status_code=400, detail=f"Invite is {inv.status}")
    if _invite_expired(inv):
        inv.status = "expired"
        db.commit()
        raise HTTPException(status_code=400, detail="Invite expired")
    if inv.email.lower() != user.email.lower():
        raise HTTPException(status_code=403, detail="Invite email does not match your account")

    _add_membership(db, inv.tenant_id, user.id)
    inv.status = "accepted"
    db.commit()
    t = db.query(Tenant).filter(Tenant.id == inv.tenant_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return t


def redeem_invite_token(db: Session, user: User, token: str) -> Tenant:
    inv = db.query(TenantInvite).filter(TenantInvite.token == token).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Invite not found")
    return redeem_invite(db, user, inv)


def redeem_pending_invites_for_user(db: Session, user: User) -> list[Tenant]:
    """Accept all pending invites addressed to this user's email."""
    email = user.email.strip().lower()
    pending = (
        db.query(TenantInvite)
        .filter(TenantInvite.email == email, TenantInvite.status == "pending")
        .all()
    )
    joined: list[Tenant] = []
    for inv in pending:
        if _invite_expired(inv):
            inv.status = "expired"
            continue
        try:
            t = redeem_invite(db, user, inv)
            joined.append(t)
        except HTTPException:
            continue
    if pending:
        db.commit()
    return joined
