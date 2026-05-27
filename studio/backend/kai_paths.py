"""Resolve Kai engine repo root (monorepo-aware defaults)."""
from __future__ import annotations

import os
from pathlib import Path


def kai_repo_root() -> Path:
    env = os.getenv("KAI_REPO")
    if env:
        return Path(env).expanduser().resolve()

    # studio/backend/kai_paths.py -> monorepo root is parents[2]
    here = Path(__file__).resolve()
    monorepo = here.parents[2]
    if (monorepo / "app.py").is_file() and (monorepo / "requirements.txt").is_file():
        return monorepo

    return Path.home() / "workspace" / "kai"


def kai_tenants_root() -> Path:
    env = os.getenv("KAI_TENANTS_ROOT")
    if env:
        return Path(env).expanduser().resolve()
    return Path.home() / "workspace"
