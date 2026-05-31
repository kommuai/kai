"""Agent training assessment — subprocess wrapper around shadou.training."""

from __future__ import annotations

import json
import os
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy.orm import Session

from shadou_paths import shadou_repo_root
from models import AgentTrainingRun, Tenant


def _python_bin() -> str:
    for candidate in (
        os.getenv("SHADOU_PYTHON"),
        "/home/ting/miniconda3/bin/python3",
        "python3",
    ):
        if candidate and Path(candidate).exists():
            return candidate
    return "python3"


def read_workspace_training(home: Path) -> dict[str, Any]:
    ws = home / "workspace.yaml"
    if not ws.is_file():
        return {}
    data = yaml.safe_load(ws.read_text(encoding="utf-8")) or {}
    t = data.get("training")
    return t if isinstance(t, dict) else {}


def _parse_earned_badges(tenant: Tenant, ws_train: dict[str, Any]) -> list[str]:
    raw = tenant.training_badges_json or "[]"
    try:
        badges = json.loads(raw)
        if isinstance(badges, list):
            return [str(b) for b in badges]
    except json.JSONDecodeError:
        pass
    ws_badges = ws_train.get("earned_badges")
    if isinstance(ws_badges, list):
        return [str(b) for b in ws_badges]
    return []


def tenant_training_summary(tenant: Tenant) -> dict[str, Any]:
    from shadou.training.levels import get_job, job_id_from_training_block, max_core_level, resolve_job_id

    ws = read_workspace_training(Path(tenant.workspace_home))
    jid = resolve_job_id(
        str(getattr(tenant, "training_job", "") or "") or job_id_from_training_block(ws)
    )
    job = get_job(jid)
    cap = max_core_level(jid)
    next_lv = tenant.training_level + 1 if tenant.training_level < cap else None
    return {
        "agent_job": jid,
        "agent_job_label": job.label if job else jid,
        "current_level": int(tenant.training_level or 0),
        "current_level_title": tenant.training_level_title or "",
        "current_level_emoji": tenant.training_level_emoji or "",
        "next_level": next_lv,
        "progress_to_next": float(tenant.training_progress_pct or 0),
        "last_assessed_at": tenant.training_last_assessed_at,
        "earned_badges": _parse_earned_badges(tenant, ws),
    }


def enrich_tenant_out(tenant: Tenant) -> dict[str, Any]:
    from schemas import AgentTrainingSummaryOut, TenantOut

    base = TenantOut.model_validate(tenant).model_dump()
    base["training_summary"] = AgentTrainingSummaryOut(**tenant_training_summary(tenant)).model_dump()
    return base


def _parse_assessment_stdout(stdout: str) -> dict[str, Any]:
    """Parse JSON from assess_all stdout (compact or pretty-printed)."""
    text = (stdout or "").strip()
    if not text:
        raise RuntimeError("assessment_empty_output")
    try:
        payload = json.loads(text)
        if isinstance(payload, dict):
            return payload
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    if start < 0:
        raise RuntimeError("assessment_empty_output")
    payload, _end = json.JSONDecoder().raw_decode(text[start:])
    if not isinstance(payload, dict):
        raise RuntimeError("assessment_invalid_output")
    return payload


def run_assessment(
    home: Path,
    *,
    level: int | None = None,
    specialization: str | None = None,
) -> dict[str, Any]:
    repo = shadou_repo_root()
    py = _python_bin()
    env = {
        **os.environ,
        "SHADOU_HOME": str(home.resolve()),
        "PYTHONPATH": str(repo),
    }
    cmd = [py, "-m", "shadou.training.assess_all", "--shadou-home", str(home.resolve()), "--compact"]
    if level is not None:
        cmd.extend(["--level", str(int(level))])
    elif specialization:
        cmd.extend(["--specialization", specialization])
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=600,
        env=env,
        cwd=str(repo),
    )
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "assessment_failed")[:500]
        raise RuntimeError(err)
    return _parse_assessment_stdout(proc.stdout or "")


def persist_assessment(
    db: Session,
    tenant: Tenant,
    *,
    user_id: str,
    result: dict[str, Any],
    duration_ms: int,
    level_filter: int | None,
    specialization_filter: str | None = None,
) -> AgentTrainingRun:
    from shadou.training.packs import ensure_tenant_training_packs

    ensure_tenant_training_packs(Path(tenant.workspace_home))

    run_id = str(uuid.uuid4())
    level_results = result.get("level_results") or {}
    if specialization_filter is not None and result.get("specialization_id"):
        passed = bool(result.get("passed"))
        gates_json = json.dumps(result.get("gates") or [])
        level_number = 0
        earned = _parse_earned_badges(tenant, read_workspace_training(Path(tenant.workspace_home)))
        if passed and specialization_filter not in earned:
            earned.append(specialization_filter)
        elif not passed:
            earned = [b for b in earned if b != specialization_filter]
        tenant.training_badges_json = json.dumps(earned)
        result = {
            "badge_results": {specialization_filter: result},
            "earned_badges": earned,
            "assessed_at": datetime.now(timezone.utc).isoformat(),
        }
    elif level_filter is not None and "level_number" in result:
        one = result
        passed = bool(one.get("passed"))
        gates_json = json.dumps(one.get("gates") or [])
        level_number = level_filter
        level_results = {level_filter: one}
        result = {
            "level_results": level_results,
            "assessed_at": datetime.now(timezone.utc).isoformat(),
        }
    elif level_filter is not None:
        one = level_results.get(level_filter) or level_results.get(str(level_filter))
        passed = bool(one.get("passed")) if isinstance(one, dict) else False
        gates_json = json.dumps(one.get("gates") or [] if isinstance(one, dict) else [])
        level_number = level_filter
    else:
        passed = int(result.get("current_level") or 0) > 0
        gates_json = json.dumps(level_results)
        level_number = int(result.get("current_level") or 0)

    run = AgentTrainingRun(
        id=run_id,
        tenant_id=tenant.id,
        level_number=level_number,
        passed=passed,
        gates_json=gates_json,
        summary_json=json.dumps(result),
        duration_ms=duration_ms,
        triggered_by_user_id=user_id,
    )
    db.add(run)

    if level_filter is None and specialization_filter is None:
        if result.get("agent_job"):
            tenant.training_job = str(result.get("agent_job"))
        tenant.training_level = int(result.get("current_level") or 0)
        tenant.training_level_title = str(result.get("current_level_title") or "")
        tenant.training_level_emoji = str(result.get("current_level_emoji") or "")
        tenant.training_progress_pct = float(result.get("progress_to_next") or 0)
        earned = result.get("earned_badges") or []
        if isinstance(earned, list):
            tenant.training_badges_json = json.dumps(earned)
        assessed = result.get("assessed_at")
        if assessed:
            try:
                tenant.training_last_assessed_at = datetime.fromisoformat(str(assessed).replace("Z", "+00:00"))
            except ValueError:
                tenant.training_last_assessed_at = datetime.now(timezone.utc)
        else:
            tenant.training_last_assessed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(tenant)
    db.refresh(run)
    return run
