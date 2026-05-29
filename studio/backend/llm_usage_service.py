"""Query LLM usage for Studio dashboard (DeepSeek token → USD)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy import text
from sqlalchemy.orm import Session

# USD totals use kai.lib.deepseek_pricing at record time; dashboard shows spend only.
from models import Tenant, TenantMembership


def _usage_match_keys(tenant_rows: list) -> list[str]:
    """Slugs plus workspace.yaml tenant.id (e.g. kommu-support) for legacy rows."""
    keys: set[str] = set()
    for row in tenant_rows:
        keys.add(row.slug)
        ws_path = Path(row.workspace_home if hasattr(row, "workspace_home") else "") / "workspace.yaml"
        if not ws_path.is_file():
            continue
        try:
            raw = yaml.safe_load(ws_path.read_text(encoding="utf-8")) or {}
            tid = str((raw.get("tenant") or {}).get("id") or "").strip()
            if tid:
                keys.add(tid)
        except Exception:
            continue
    return sorted(keys)


def _period_start(period: str) -> datetime:
    now = datetime.now(timezone.utc)
    if period == "month":
        return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    # default: rolling 24h
    return now - timedelta(hours=24)


def _daily_chart_start(days: int = 14) -> datetime:
    now = datetime.now(timezone.utc)
    start = (now - timedelta(days=days - 1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return start


def _build_daily_series(
    db: Session,
    *,
    match_keys: list[str],
    days: int = 14,
) -> list[dict[str, Any]]:
    """One bucket per UTC calendar day (zeros for days with no usage)."""
    if not match_keys:
        return []

    start = _daily_chart_start(days)
    since = start.isoformat()
    placeholders = ", ".join(f":s{i}" for i in range(len(match_keys)))
    params: dict[str, Any] = {f"s{i}": s for i, s in enumerate(match_keys)}
    params["since"] = since

    daily_sql = text(
        f"""
        SELECT
          substr(created_at, 1, 10) AS day,
          COALESCE(SUM(total_tokens), 0) AS total_tokens,
          COALESCE(SUM(cost_usd), 0) AS cost_usd,
          COUNT(*) AS request_count
        FROM llm_usage_events
        WHERE created_at >= :since
          AND tenant_slug IN ({placeholders})
        GROUP BY day
        ORDER BY day
        """
    )
    rows = {r["day"]: dict(r) for r in db.execute(daily_sql, params).mappings().all()}

    series: list[dict[str, Any]] = []
    for i in range(days):
        d = (start + timedelta(days=i)).date().isoformat()
        row = rows.get(d) or {}
        series.append(
            {
                "date": d,
                "total_tokens": int(row.get("total_tokens") or 0),
                "cost_usd": round(float(row.get("cost_usd") or 0), 6),
                "request_count": int(row.get("request_count") or 0),
            }
        )
    return series


def get_deepseek_usage_summary(db: Session, user_id: str, *, period: str = "day") -> dict[str, Any]:
    since = _period_start(period).isoformat()

    tenant_rows = (
        db.query(Tenant.id, Tenant.slug, Tenant.display_name, Tenant.workspace_home)
        .join(TenantMembership, TenantMembership.tenant_id == Tenant.id)
        .filter(TenantMembership.user_id == user_id)
        .all()
    )
    match_keys = _usage_match_keys(tenant_rows)
    if not match_keys:
        return _empty_summary(period, since)

    daily = _build_daily_series(db, match_keys=match_keys)

    placeholders = ", ".join(f":s{i}" for i in range(len(match_keys)))
    params: dict[str, Any] = {f"s{i}": s for i, s in enumerate(match_keys)}
    params["since"] = since

    per_tenant_sql = text(
        f"""
        SELECT
          tenant_slug,
          COALESCE(SUM(prompt_tokens), 0) AS prompt_tokens,
          COALESCE(SUM(completion_tokens), 0) AS completion_tokens,
          COALESCE(SUM(cached_prompt_tokens), 0) AS cached_prompt_tokens,
          COALESCE(SUM(total_tokens), 0) AS total_tokens,
          COALESCE(SUM(cost_usd), 0) AS cost_usd,
          COUNT(*) AS request_count
        FROM llm_usage_events
        WHERE created_at >= :since
          AND tenant_slug IN ({placeholders})
        GROUP BY tenant_slug
        """
    )
    rows = db.execute(per_tenant_sql, params).mappings().all()
    # Roll up manifest ids (kommu-support) onto Studio slug (kommu) for display.
    by_slug: dict[str, dict] = {}
    for r in rows:
        key = r["tenant_slug"]
        if key not in by_slug:
            by_slug[key] = dict(r)
        else:
            prev = by_slug[key]
            by_slug[key] = {
                "tenant_slug": key,
                "prompt_tokens": int(prev["prompt_tokens"]) + int(r["prompt_tokens"]),
                "completion_tokens": int(prev["completion_tokens"]) + int(r["completion_tokens"]),
                "cached_prompt_tokens": int(prev["cached_prompt_tokens"]) + int(r["cached_prompt_tokens"]),
                "total_tokens": int(prev["total_tokens"]) + int(r["total_tokens"]),
                "cost_usd": float(prev["cost_usd"]) + float(r["cost_usd"]),
                "request_count": int(prev["request_count"]) + int(r["request_count"]),
            }

    slug_keys = {t.slug for t in tenant_rows}
    manifest_to_slug: dict[str, str] = {}
    for t in tenant_rows:
        for mk in match_keys:
            if mk != t.slug and mk not in slug_keys:
                manifest_to_slug[mk] = t.slug

    tenants_out = []
    totals = {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "cached_prompt_tokens": 0,
        "total_tokens": 0,
        "cost_usd": 0.0,
        "request_count": 0,
    }
    for t in tenant_rows:
        agg = dict(by_slug.get(t.slug) or {})
        for mk, target in manifest_to_slug.items():
            if target == t.slug and mk in by_slug:
                extra = by_slug[mk]
                agg = {
                    "prompt_tokens": int(agg.get("prompt_tokens", 0)) + int(extra["prompt_tokens"]),
                    "completion_tokens": int(agg.get("completion_tokens", 0)) + int(extra["completion_tokens"]),
                    "cached_prompt_tokens": int(agg.get("cached_prompt_tokens", 0)) + int(extra["cached_prompt_tokens"]),
                    "total_tokens": int(agg.get("total_tokens", 0)) + int(extra["total_tokens"]),
                    "cost_usd": float(agg.get("cost_usd", 0)) + float(extra["cost_usd"]),
                    "request_count": int(agg.get("request_count", 0)) + int(extra["request_count"]),
                }
        if not agg:
            agg = {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "cached_prompt_tokens": 0,
                "total_tokens": 0,
                "cost_usd": 0.0,
                "request_count": 0,
            }
        cost = float(agg.get("cost_usd", 0))
        tenants_out.append(
            {
                "tenant_id": t.id,
                "slug": t.slug,
                "display_name": t.display_name,
                "prompt_tokens": int(agg["prompt_tokens"]),
                "completion_tokens": int(agg["completion_tokens"]),
                "cached_prompt_tokens": int(agg["cached_prompt_tokens"]),
                "total_tokens": int(agg["total_tokens"]),
                "cost_usd": round(cost, 6),
                "request_count": int(agg["request_count"]),
            }
        )
        totals["prompt_tokens"] += int(agg["prompt_tokens"])
        totals["completion_tokens"] += int(agg["completion_tokens"])
        totals["cached_prompt_tokens"] += int(agg["cached_prompt_tokens"])
        totals["total_tokens"] += int(agg["total_tokens"])
        totals["cost_usd"] += cost
        totals["request_count"] += int(agg["request_count"])

    # Sources breakdown (all user tenants)
    sources_sql = text(
        f"""
        SELECT source,
          COALESCE(SUM(prompt_tokens), 0) AS prompt_tokens,
          COALESCE(SUM(completion_tokens), 0) AS completion_tokens,
          COALESCE(SUM(cost_usd), 0) AS cost_usd,
          COUNT(*) AS request_count
        FROM llm_usage_events
        WHERE created_at >= :since
          AND tenant_slug IN ({placeholders})
        GROUP BY source
        ORDER BY cost_usd DESC
        """
    )
    sources = [dict(r) for r in db.execute(sources_sql, params).mappings().all()]

    return {
        "period": period,
        "since": since,
        "totals": {
            **totals,
            "cost_usd": round(totals["cost_usd"], 6),
        },
        "tenants": tenants_out,
        "by_source": sources,
        "daily": daily,
    }


def _empty_summary(period: str, since: str) -> dict[str, Any]:
    days = 14
    start = _daily_chart_start(days)
    daily = [
        {
            "date": (start + timedelta(days=i)).date().isoformat(),
            "total_tokens": 0,
            "cost_usd": 0.0,
            "request_count": 0,
        }
        for i in range(days)
    ]
    return {
        "period": period,
        "since": since,
        "totals": {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "cached_prompt_tokens": 0,
            "total_tokens": 0,
            "cost_usd": 0.0,
            "request_count": 0,
        },
        "tenants": [],
        "by_source": [],
        "daily": daily,
    }
