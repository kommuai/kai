"""Kai Admin UI — FastAPI backend."""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Monorepo root so `import kai` works for compile/capabilities helpers.
_repo = Path(__file__).resolve().parents[2]
if (_repo / "kai").is_dir() and str(_repo) not in sys.path:
    sys.path.insert(0, str(_repo))

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from auth import decode_token
from database import DB_DIR, get_db, init_db
from deps import get_current_user
from models import User
from routers.ai_assist_router import router as ai_assist_router
from routers.auth_router import router as auth_router
from routers.hitl_router import router as hitl_router
from routers.inbox_router import router as inbox_router
from routers.onboarding_router import router as onboarding_router
from routers.tenants_router import router as tenants_router
from routers.usage_router import router as usage_router
from routers.whatsapp_router import router as whatsapp_router
from schemas import UserOut

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

app = FastAPI(title="Kai Admin API", version="1.0.0", docs_url="/api/docs", redoc_url=None)

_cors_origins = {
    FRONTEND_URL,
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:4173",
    "http://127.0.0.1:4173",
}
_extra = os.getenv("CORS_EXTRA_ORIGINS", "")
if _extra:
    _cors_origins.update(o.strip() for o in _extra.split(",") if o.strip())

app.add_middleware(
    CORSMiddleware,
    allow_origins=sorted(_cors_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(tenants_router)
app.include_router(onboarding_router)
app.include_router(whatsapp_router)
app.include_router(ai_assist_router)
app.include_router(hitl_router)
app.include_router(inbox_router)
app.include_router(usage_router)


@app.on_event("startup")
def on_startup():
    if not os.getenv("KAI_ADMIN_DB_DIR"):
        os.environ["KAI_ADMIN_DB_DIR"] = str(DB_DIR)
    init_db()


@app.get("/auth/me", response_model=UserOut, tags=["auth"])
def me(user: User = Depends(get_current_user)):
    return user


@app.get("/health")
def health():
    return {"ok": True}
