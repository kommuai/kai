"""Kai Admin UI — FastAPI backend."""
from __future__ import annotations

import os

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from auth import decode_token
from database import get_db, init_db
from deps import get_current_user
from models import User
from routers.auth_router import router as auth_router
from routers.inbox_router import router as inbox_router
from routers.tenants_router import router as tenants_router
from schemas import UserOut

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

app = FastAPI(title="Kai Admin API", version="1.0.0", docs_url="/api/docs", redoc_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL, "http://localhost:5173", "http://localhost:4173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(tenants_router)
app.include_router(inbox_router)


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/auth/me", response_model=UserOut, tags=["auth"])
def me(user: User = Depends(get_current_user)):
    return user


@app.get("/health")
def health():
    return {"ok": True}
