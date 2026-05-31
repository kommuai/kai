"""Agent Training Academy — certification levels and specialization badges API."""

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from deps import get_current_user
from models import AgentTrainingRun, User
from routers.tenants_router import _assert_tenant_member
from schemas import (
    TrainingAssessIn,
    TrainingAssessOut,
    TrainingBadgeResultOut,
    TrainingGateOut,
    TrainingLevelDefOut,
    TrainingLevelResultOut,
    TrainingQuestOut,
    TrainingRunOut,
    TrainingSpecializationDefOut,
    TrainingStatusOut,
)
from training_service import (
    _parse_earned_badges,
    persist_assessment,
    read_workspace_training,
    run_assessment,
)

router = APIRouter(prefix="/tenants", tags=["training"])


def _resolve_tenant_job(tenant, ws_train: dict) -> str:
    from shadou.training.levels import job_id_from_training_block, resolve_job_id

    return resolve_job_id(
        str(getattr(tenant, "training_job", "") or "") or job_id_from_training_block(ws_train)
    )


def _level_defs(job_id: str) -> list[TrainingLevelDefOut]:
    from shadou.training.levels import levels_dict_for_api

    return [TrainingLevelDefOut(**row) for row in levels_dict_for_api(job_id)]


def _specialization_defs(job_id: str) -> list[TrainingSpecializationDefOut]:
    from shadou.training.levels import specializations_dict_for_api

    return [TrainingSpecializationDefOut(**row) for row in specializations_dict_for_api(job_id)]


def _parse_level_results(raw: dict[str, Any]) -> dict[int, TrainingLevelResultOut]:
    out: dict[int, TrainingLevelResultOut] = {}
    for key, val in (raw or {}).items():
        if not isinstance(val, dict):
            continue
        try:
            num = int(key)
        except (TypeError, ValueError):
            continue
        out[num] = TrainingLevelResultOut(
            level_number=num,
            title=str(val.get("title") or ""),
            passed=bool(val.get("passed")),
            score_pct=float(val.get("score_pct") or 0),
            gates=[TrainingGateOut(**g) for g in (val.get("gates") or []) if isinstance(g, dict)],
            quests=[TrainingQuestOut(**q) for q in (val.get("quests") or []) if isinstance(q, dict)],
        )
    return out


def _parse_badge_results(raw: dict[str, Any]) -> dict[str, TrainingBadgeResultOut]:
    out: dict[str, TrainingBadgeResultOut] = {}
    for key, val in (raw or {}).items():
        if not isinstance(val, dict):
            continue
        spec_id = str(val.get("specialization_id") or key)
        out[spec_id] = TrainingBadgeResultOut(
            specialization_id=spec_id,
            branch=str(val.get("branch") or ""),
            title=str(val.get("title") or ""),
            passed=bool(val.get("passed")),
            score_pct=float(val.get("score_pct") or 0),
            locked=bool(val.get("locked")),
            lock_reason=str(val.get("lock_reason") or ""),
            gates=[TrainingGateOut(**g) for g in (val.get("gates") or []) if isinstance(g, dict)],
            quests=[TrainingQuestOut(**q) for q in (val.get("quests") or []) if isinstance(q, dict)],
        )
    return out


@router.get("/{tenant_id}/training", response_model=TrainingStatusOut)
def get_training_status(
    tenant_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from shadou.training.levels import get_job, get_level, max_core_level

    tenant = _assert_tenant_member(tenant_id, user, db)
    home = Path(tenant.workspace_home)
    ws_train = read_workspace_training(home)
    jid = _resolve_tenant_job(tenant, ws_train)
    job = get_job(jid)

    last_run = (
        db.query(AgentTrainingRun)
        .filter(AgentTrainingRun.tenant_id == tenant.id)
        .order_by(AgentTrainingRun.created_at.desc())
        .first()
    )
    level_results: dict[int, TrainingLevelResultOut] = {}
    badge_results: dict[str, TrainingBadgeResultOut] = {}
    if last_run and last_run.summary_json:
        try:
            summary = json.loads(last_run.summary_json)
            level_results = _parse_level_results(summary.get("level_results") or {})
            badge_results = _parse_badge_results(summary.get("badge_results") or {})
        except json.JSONDecodeError:
            pass

    current_level = int(tenant.training_level or ws_train.get("current_level") or 0)
    cap = max_core_level(jid)
    next_level = current_level + 1 if current_level < cap else None
    quests_next: list[TrainingQuestOut] = []
    if next_level and next_level in level_results:
        quests_next = level_results[next_level].quests
    elif next_level:
        lv = get_level(next_level, jid)
        if lv:
            quests_next = [TrainingQuestOut(id=r.id, text=r.text, done=False) for r in lv.requirements]

    earned = _parse_earned_badges(tenant, ws_train)

    return TrainingStatusOut(
        agent_job=jid,
        agent_job_label=job.label if job else jid,
        levels=_level_defs(jid),
        specializations=_specialization_defs(jid),
        current_level=current_level,
        current_level_title=tenant.training_level_title or str(ws_train.get("current_level_title") or ""),
        current_level_emoji=tenant.training_level_emoji or str(ws_train.get("current_level_emoji") or ""),
        next_level=next_level,
        progress_to_next=float(tenant.training_progress_pct or 0),
        last_assessed_at=tenant.training_last_assessed_at,
        level_results=level_results,
        badge_results=badge_results,
        earned_badges=earned,
        quests_next=quests_next,
    )


@router.post("/{tenant_id}/training/assess", response_model=TrainingAssessOut)
def run_training_assess(
    tenant_id: str,
    body: TrainingAssessIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from shadou.training.levels import get_specialization, max_core_level

    tenant = _assert_tenant_member(tenant_id, user, db)
    home = Path(tenant.workspace_home)
    if not home.is_dir():
        raise HTTPException(status_code=400, detail="workspace_missing")

    ws_train = read_workspace_training(home)
    jid = _resolve_tenant_job(tenant, ws_train)

    if body.level is not None and body.specialization:
        raise HTTPException(status_code=400, detail="specify_level_or_specialization_not_both")

    cap = max_core_level(jid)
    if body.level is not None and not (1 <= body.level <= cap):
        raise HTTPException(status_code=400, detail=f"level_must_be_1_to_{cap}")

    if body.specialization is not None and get_specialization(body.specialization, jid) is None:
        raise HTTPException(status_code=400, detail="unknown_specialization")

    start = time.time()
    try:
        result = run_assessment(home, level=body.level, specialization=body.specialization)
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="assessment_timed_out") from None
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)[:300]) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)[:300]) from exc

    duration_ms = int((time.time() - start) * 1000)
    run = persist_assessment(
        db,
        tenant,
        user_id=user.id,
        result=result,
        duration_ms=duration_ms,
        level_filter=body.level,
        specialization_filter=body.specialization,
    )

    return TrainingAssessOut(
        run_id=run.id,
        status="completed",
        summary=result,
    )


@router.get("/{tenant_id}/training/runs", response_model=list[TrainingRunOut])
def list_training_runs(
    tenant_id: str,
    limit: int = 20,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tenant = _assert_tenant_member(tenant_id, user, db)
    runs = (
        db.query(AgentTrainingRun)
        .filter(AgentTrainingRun.tenant_id == tenant.id)
        .order_by(AgentTrainingRun.created_at.desc())
        .limit(min(limit, 100))
        .all()
    )
    out: list[TrainingRunOut] = []
    for r in runs:
        try:
            summary = json.loads(r.summary_json)
        except json.JSONDecodeError:
            summary = {}
        out.append(
            TrainingRunOut(
                id=r.id,
                tenant_id=r.tenant_id,
                level_number=r.level_number,
                passed=r.passed,
                duration_ms=r.duration_ms,
                created_at=r.created_at,
                summary=summary,
            )
        )
    return out


@router.get("/{tenant_id}/training/runs/{run_id}")
def get_training_run(
    tenant_id: str,
    run_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tenant = _assert_tenant_member(tenant_id, user, db)
    run = (
        db.query(AgentTrainingRun)
        .filter(AgentTrainingRun.id == run_id, AgentTrainingRun.tenant_id == tenant.id)
        .first()
    )
    if not run:
        raise HTTPException(status_code=404, detail="run_not_found")
    try:
        summary = json.loads(run.summary_json)
    except json.JSONDecodeError:
        summary = {}
    failures: list[dict[str, Any]] = []
    if isinstance(summary.get("level_results"), dict):
        for lv in summary["level_results"].values():
            if isinstance(lv, dict):
                failures.extend(lv.get("failures") or [])
    return {
        "id": run.id,
        "level_number": run.level_number,
        "passed": run.passed,
        "duration_ms": run.duration_ms,
        "created_at": run.created_at,
        "summary": summary,
        "failures": failures[:50],
    }
