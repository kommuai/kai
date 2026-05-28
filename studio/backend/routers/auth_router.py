"""Auth endpoints: email/password, Google OAuth, Facebook OAuth."""
from __future__ import annotations

import os
import uuid
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from auth import create_access_token, hash_password, verify_password
from database import get_db
from models import User
from schemas import LoginRequest, SignupRequest, TokenResponse, UserOut
from invite_service import redeem_pending_invites_for_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/providers")
def list_providers():
    """Return which OAuth providers are configured."""
    return {
        "google": bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET),
        "facebook": bool(FB_APP_ID and FB_APP_SECRET),
    }

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

# Google OAuth
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8080/auth/google/callback")

# Facebook OAuth
FB_APP_ID = os.getenv("FACEBOOK_APP_ID", "")
FB_APP_SECRET = os.getenv("FACEBOOK_APP_SECRET", "")
FB_REDIRECT_URI = os.getenv("FACEBOOK_REDIRECT_URI", "http://localhost:8080/auth/facebook/callback")


def _make_token_response(user: User) -> dict:
    token = create_access_token(user.id, user.email)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": UserOut.model_validate(user),
    }


# ── Email / Password ──────────────────────────────────────────────────────────

def _email_lookup(db: Session, email: str):
    normalized = email.strip().lower()
    return db.query(User).filter(func.lower(User.email) == normalized).first()


@router.post("/signup", response_model=TokenResponse)
def signup(body: SignupRequest, db: Session = Depends(get_db)):
    email = body.email.strip().lower()
    if _email_lookup(db, email):
        raise HTTPException(status_code=400, detail="An account with this email already exists. Try signing in.")
    user = User(
        id=str(uuid.uuid4()),
        email=email,
        name=body.name,
        password_hash=hash_password(body.password),
        provider="email",
        is_verified=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    redeem_pending_invites_for_user(db, user)
    return _make_token_response(user)


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    email = body.email.strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="Email is required.")
    if not body.password:
        raise HTTPException(status_code=400, detail="Password is required.")

    user = _email_lookup(db, email)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    if not user.password_hash:
        provider = (user.provider or "social").capitalize()
        if user.provider == "google":
            raise HTTPException(
                status_code=401,
                detail="This account uses Google sign-in. Use “Continue with Google” below.",
            )
        if user.provider == "facebook":
            raise HTTPException(
                status_code=401,
                detail="This account uses Facebook sign-in. Use “Continue with Facebook” below.",
            )
        raise HTTPException(
            status_code=401,
            detail=f"This account uses {provider} sign-in, not a password.",
        )

    if not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    redeem_pending_invites_for_user(db, user)
    return _make_token_response(user)


# ── Google OAuth ──────────────────────────────────────────────────────────────

@router.get("/google")
def google_login():
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=503, detail="Google OAuth not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.")
    params = (
        f"response_type=code"
        f"&client_id={GOOGLE_CLIENT_ID}"
        f"&redirect_uri={GOOGLE_REDIRECT_URI}"
        f"&scope=openid%20email%20profile"
        f"&access_type=offline"
    )
    return RedirectResponse(f"https://accounts.google.com/o/oauth2/v2/auth?{params}")


@router.get("/google/callback")
def google_callback(code: str, db: Session = Depends(get_db)):
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=503, detail="Google OAuth not configured")

    with httpx.Client() as client:
        token_resp = client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        )
        token_data: dict[str, Any] = token_resp.json()
        access_token = token_data.get("access_token", "")
        if not access_token:
            raise HTTPException(status_code=400, detail="Failed to get Google access token")

        userinfo_resp = client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        info: dict[str, Any] = userinfo_resp.json()

    email = info.get("email", "")
    if not email:
        raise HTTPException(status_code=400, detail="Google did not return an email")

    email = email.strip().lower()
    user = _email_lookup(db, email)
    if not user:
        user = User(
            id=str(uuid.uuid4()),
            email=email,
            name=info.get("name", email.split("@")[0]),
            avatar_url=info.get("picture", ""),
            provider="google",
            provider_id=str(info.get("id", "")),
            is_verified=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    redeem_pending_invites_for_user(db, user)
    jwt_token = create_access_token(user.id, user.email)
    return RedirectResponse(f"{FRONTEND_URL}/auth/callback?token={jwt_token}")


# ── Facebook OAuth ────────────────────────────────────────────────────────────

@router.get("/facebook")
def facebook_login():
    if not FB_APP_ID:
        raise HTTPException(status_code=503, detail="Facebook OAuth not configured. Set FACEBOOK_APP_ID and FACEBOOK_APP_SECRET.")
    params = (
        f"client_id={FB_APP_ID}"
        f"&redirect_uri={FB_REDIRECT_URI}"
        f"&scope=email,public_profile"
    )
    return RedirectResponse(f"https://www.facebook.com/v18.0/dialog/oauth?{params}")


@router.get("/facebook/callback")
def facebook_callback(code: str, db: Session = Depends(get_db)):
    if not FB_APP_ID:
        raise HTTPException(status_code=503, detail="Facebook OAuth not configured")

    with httpx.Client() as client:
        token_resp = client.get(
            "https://graph.facebook.com/v18.0/oauth/access_token",
            params={
                "client_id": FB_APP_ID,
                "redirect_uri": FB_REDIRECT_URI,
                "client_secret": FB_APP_SECRET,
                "code": code,
            },
        )
        token_data: dict[str, Any] = token_resp.json()
        access_token = token_data.get("access_token", "")
        if not access_token:
            raise HTTPException(status_code=400, detail="Failed to get Facebook access token")

        me_resp = client.get(
            "https://graph.facebook.com/me",
            params={"fields": "id,name,email,picture", "access_token": access_token},
        )
        info: dict[str, Any] = me_resp.json()

    email = info.get("email", "")
    if not email:
        raise HTTPException(status_code=400, detail="Facebook did not return an email. Enable email permission.")

    email = email.strip().lower()
    user = _email_lookup(db, email)
    if not user:
        user = User(
            id=str(uuid.uuid4()),
            email=email,
            name=info.get("name", email.split("@")[0]),
            avatar_url=(info.get("picture", {}).get("data", {}).get("url", "") if isinstance(info.get("picture"), dict) else ""),
            provider="facebook",
            provider_id=str(info.get("id", "")),
            is_verified=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    redeem_pending_invites_for_user(db, user)
    jwt_token = create_access_token(user.id, user.email)
    return RedirectResponse(f"{FRONTEND_URL}/auth/callback?token={jwt_token}")


@router.get("/me", response_model=UserOut)
def me(db: Session = Depends(get_db), token: str = ""):
    from deps import get_current_user
    from fastapi.security import HTTPAuthorizationCredentials
    # handled via the dependency in the actual app
    raise HTTPException(status_code=400, detail="Use Bearer token")
