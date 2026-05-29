"""Persist LLM token usage for Kai Studio dashboard (shared SQLite admin DB)."""
from __future__ import annotations

import logging
import os
import sqlite3
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from kai.lib.deepseek_pricing import (
    OFFICIAL_PRICING_URL,
    compute_usage_cost_usd,
    parse_openai_usage,
)

log = logging.getLogger("kai.llm_usage")

# Optional attribution for engine calls (tenant slug from workspace manifest).
usage_tenant_slug: ContextVar[str | None] = ContextVar("usage_tenant_slug", default=None)
usage_source: ContextVar[str | None] = ContextVar("usage_source", default=None)


def resolve_usage_tenant_slug(explicit: str | None = None) -> str | None:
    """Studio dashboard keys tenants by slug (e.g. kommu); workspace manifest may use tenant.id (kommu-support)."""
    home = (os.getenv("KAI_HOME") or "").strip()
    if home:
        name = Path(home).name
        if name.startswith("kai-tenant-"):
            return name.removeprefix("kai-tenant-")
    if explicit and str(explicit).strip():
        return str(explicit).strip()
    try:
        from kai.workspace.manifest import load_manifest

        return (load_manifest().tenant_id or "").strip() or None
    except Exception:
        return None


def _admin_db_path() -> Path | None:
    raw = (os.getenv("KAI_ADMIN_DB_DIR") or "").strip()
    if not raw:
        return None
    return Path(raw) / "admin.db"


def _ensure_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS llm_usage_events (
          id TEXT PRIMARY KEY,
          tenant_slug TEXT,
          source TEXT NOT NULL,
          model TEXT NOT NULL,
          prompt_tokens INTEGER NOT NULL DEFAULT 0,
          completion_tokens INTEGER NOT NULL DEFAULT 0,
          cached_prompt_tokens INTEGER NOT NULL DEFAULT 0,
          total_tokens INTEGER NOT NULL DEFAULT 0,
          cost_usd REAL NOT NULL,
          pricing_model_key TEXT NOT NULL,
          created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS ix_llm_usage_events_created_at ON llm_usage_events(created_at)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS ix_llm_usage_events_tenant_slug ON llm_usage_events(tenant_slug)"
    )


def record_openai_usage(
    *,
    model: str,
    usage: Any,
    source: str | None = None,
    tenant_slug: str | None = None,
) -> dict[str, Any] | None:
    """Parse usage, compute USD, append row when KAI_ADMIN_DB_DIR is set."""
    parsed = parse_openai_usage(usage)
    if parsed is None:
        return None
    try:
        cost = compute_usage_cost_usd(model, parsed)
    except ValueError:
        log.debug("Skipping usage record: unknown model %r", model)
        return None

    slug = tenant_slug if tenant_slug is not None else usage_tenant_slug.get()
    src = source or usage_source.get() or "engine"
    return _insert_event(
        tenant_slug=slug,
        source=src,
        model=model,
        usage=parsed,
        cost_usd=float(cost.usd),
        pricing_model_key=cost.model,
    )


def record_usage_counts(
    *,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    cached_prompt_tokens: int = 0,
    source: str,
    tenant_slug: str | None = None,
) -> dict[str, Any] | None:
    from kai.lib.deepseek_pricing import TokenUsage

    usage = TokenUsage(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        cached_prompt_tokens=cached_prompt_tokens,
    )
    try:
        cost = compute_usage_cost_usd(model, usage)
    except ValueError:
        return None
    slug = resolve_usage_tenant_slug(tenant_slug)
    return _insert_event(
        tenant_slug=slug,
        source=source,
        model=model,
        usage=usage,
        cost_usd=float(cost.usd),
        pricing_model_key=cost.model,
    )


def _insert_event(
    *,
    tenant_slug: str | None,
    source: str,
    model: str,
    usage: Any,
    cost_usd: float,
    pricing_model_key: str,
) -> dict[str, Any] | None:
    db_path = _admin_db_path()
    if db_path is None:
        return None
    if not db_path.is_file():
        log.debug("Admin DB not found at %s — usage not recorded", db_path)
        return None

    event_id = str(uuid.uuid4())
    created = datetime.now(timezone.utc).isoformat()
    row = {
        "id": event_id,
        "tenant_slug": tenant_slug,
        "source": source,
        "model": model,
        "prompt_tokens": usage.prompt_tokens,
        "completion_tokens": usage.completion_tokens,
        "cached_prompt_tokens": usage.cached_prompt_tokens,
        "total_tokens": usage.total_tokens,
        "cost_usd": cost_usd,
        "pricing_model_key": pricing_model_key,
        "created_at": created,
        "pricing_url": OFFICIAL_PRICING_URL,
    }
    try:
        with sqlite3.connect(db_path) as conn:
            _ensure_table(conn)
            conn.execute(
                """
                INSERT INTO llm_usage_events (
                  id, tenant_slug, source, model,
                  prompt_tokens, completion_tokens, cached_prompt_tokens, total_tokens,
                  cost_usd, pricing_model_key, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_id,
                    tenant_slug,
                    source,
                    model,
                    usage.prompt_tokens,
                    usage.completion_tokens,
                    usage.cached_prompt_tokens,
                    usage.total_tokens,
                    cost_usd,
                    pricing_model_key,
                    created,
                ),
            )
            conn.commit()
    except Exception:
        log.exception("Failed to record LLM usage")
        return None
    return row


def set_usage_context(*, tenant_slug: str | None = None, source: str | None = None) -> None:
    if tenant_slug is not None:
        usage_tenant_slug.set(tenant_slug)
    if source is not None:
        usage_source.set(source)
