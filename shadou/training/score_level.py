"""Score a single training level for a tenant workspace."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from shadou.training.levels import (
    LevelDef,
    SpecializationDef,
    get_level,
    get_specialization,
    job_id_from_shadou_home,
    resolve_job_id,
)
from shadou.training.packs import ensure_tenant_training_packs, eval_pack_path
from shadou.training.scorers import check_gates, compute_metrics
from shadou.tools.eval_run import _load_eval_items, run_eval


@dataclass
class LevelAssessment:
    level_number: int
    level_id: str
    title: str
    passed: bool
    score_pct: float
    gates: list[dict[str, Any]] = field(default_factory=list)
    quests: list[dict[str, Any]] = field(default_factory=list)
    metrics: dict[str, float | None] = field(default_factory=dict)
    eval_total: int = 0
    failures: list[dict[str, Any]] = field(default_factory=list)
    specialization_id: str = ""
    branch: str = ""

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "level_number": self.level_number,
            "level_id": self.level_id,
            "title": self.title,
            "passed": self.passed,
            "score_pct": self.score_pct,
            "gates": self.gates,
            "quests": self.quests,
            "metrics": self.metrics,
            "eval_total": self.eval_total,
            "failures": self.failures[:20],
        }
        if self.specialization_id:
            out["specialization_id"] = self.specialization_id
            out["branch"] = self.branch
        return out


def _quest_status(
    level: LevelDef | SpecializationDef,
    metrics: dict[str, float | None],
    gate_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    gate_ok = {g["name"]: g.get("ok") for g in gate_rows}
    quests: list[dict[str, Any]] = []
    for req in level.requirements:
        done = bool(gate_ok) and all(gate_ok.values()) if len(level.gates) <= 1 else None
        if req.id == "faq_basics":
            v = metrics.get("accuracy_level1_faq")
            done = v is not None and v >= level.gates.get("accuracy_level1_faq", 0.7)
        elif req.id == "no_invent":
            v = metrics.get("abstention_utility")
            done = v is not None and v >= level.gates.get("abstention_utility", 0.8)
        elif req.id == "escalate_unknown":
            v = metrics.get("escalation_correct_rate")
            done = v is not None and v >= level.gates.get("escalation_correct_rate", 0.85)
        elif req.id in ("top20", "complex_resolve"):
            key = "accuracy_level2_common" if req.id == "top20" else "resolution_rate"
            v = metrics.get(key)
            th = level.gates.get(key, 0.7)
            done = v is not None and v >= th
        elif req.id == "troubleshooting_flow":
            v = metrics.get("workflow_step_score")
            done = v is not None and v >= level.gates.get("workflow_step_score", 0.8)
        elif req.id == "no_guesses":
            v = metrics.get("no_guess_rate")
            done = v is not None and v >= level.gates.get("no_guess_rate", 0.9)
        elif req.id == "ticket_type":
            v = metrics.get("ticket_type_accuracy")
            done = v is not None and v >= level.gates.get("ticket_type_accuracy", 0.85)
        elif req.id == "handoff_summary":
            v = metrics.get("handoff_summary_score")
            done = v is not None and v >= level.gates.get("handoff_summary_score", 0.7)
        elif req.id == "paraphrase":
            v = metrics.get("paraphrase_consistency")
            done = v is not None and v >= level.gates.get("paraphrase_consistency", 0.8)
        elif req.id == "end_to_end":
            v = metrics.get("resolution_rate")
            done = v is not None and v >= level.gates.get("resolution_rate", 0.8)
        elif req.id == "safe_tools":
            v = metrics.get("tool_usage_correct")
            done = v is not None and v >= level.gates.get("tool_usage_correct", 0.9)
        elif req.id.startswith("product_") or req.id.startswith("pricing") or req.id.startswith("objection"):
            v = metrics.get("accuracy_badge_sales")
            done = v is not None and v >= level.gates.get("accuracy_badge_sales", 0.75)
        elif req.id in ("troubleshoot_steps", "known_issue_match", "evidence_collect", "eng_escalate"):
            v = metrics.get("accuracy_badge_technical") or metrics.get("workflow_step_score")
            th = level.gates.get("accuracy_badge_technical", 0.75)
            done = v is not None and v >= th
        elif req.id in ("order_status", "shipping_timeline", "delivery_issues", "address_changes"):
            v = metrics.get("accuracy_badge_logistics")
            done = v is not None and v >= level.gates.get("accuracy_badge_logistics", 0.75)
        else:
            done = all(g.get("ok") for g in gate_rows) if gate_rows else False
        quests.append({"id": req.id, "text": req.text, "done": bool(done)})
    return quests


def assess_level(
    shadou_home: Path,
    level_number: int,
    *,
    job_id: str | None = None,
    user_id: str = "training_harness",
) -> LevelAssessment:
    shadou_home = Path(shadou_home).resolve()
    jid = resolve_job_id(job_id or job_id_from_shadou_home(shadou_home))
    level = get_level(level_number, jid)
    if level is None:
        raise ValueError(f"unknown_level:{level_number}")

    prev_home = os.environ.get("SHADOU_HOME")
    os.environ["SHADOU_HOME"] = str(shadou_home)
    try:
        ensure_tenant_training_packs(shadou_home, jid)
        pack = eval_pack_path(shadou_home, level.eval_pack)
        items = _load_eval_items(pack)
        if not items:
            return LevelAssessment(
                level_number=level_number,
                level_id=level.id,
                title=level.title,
                passed=False,
                score_pct=0.0,
                gates=[],
                quests=[{"id": r.id, "text": r.text, "done": False} for r in level.requirements],
                eval_total=0,
            )

        eval_results = run_eval(items, user_id=user_id)
        metrics = compute_metrics(eval_results, eval_items=items)

        # verification_flag_rate_max gate uses inverted check
        gate_rows = check_gates(level.gates, metrics)
        passed = bool(gate_rows) and all(g.get("ok") for g in gate_rows)
        ok_count = sum(1 for g in gate_rows if g.get("ok"))
        score_pct = round(ok_count / len(gate_rows), 4) if gate_rows else 0.0

        quests = _quest_status(level, metrics, gate_rows)
        failures = [ir for ir in eval_results.get("items") or [] if not ir.get("passed")]

        return LevelAssessment(
            level_number=level_number,
            level_id=level.id,
            title=level.title,
            passed=passed,
            score_pct=score_pct,
            gates=gate_rows,
            quests=quests,
            metrics={k: v for k, v in metrics.items() if v is not None},
            eval_total=int(eval_results.get("total") or 0),
            failures=failures,
        )
    finally:
        if prev_home is None:
            os.environ.pop("SHADOU_HOME", None)
        else:
            os.environ["SHADOU_HOME"] = prev_home


def assess_specialization(
    shadou_home: Path,
    specialization_id: str,
    *,
    job_id: str | None = None,
    user_id: str = "training_harness",
) -> LevelAssessment:
    shadou_home = Path(shadou_home).resolve()
    jid = resolve_job_id(job_id or job_id_from_shadou_home(shadou_home))
    spec = get_specialization(specialization_id, jid)
    if spec is None:
        raise ValueError(f"unknown_specialization:{specialization_id}")

    prev_home = os.environ.get("SHADOU_HOME")
    os.environ["SHADOU_HOME"] = str(shadou_home)
    try:
        ensure_tenant_training_packs(shadou_home, jid)
        pack = eval_pack_path(shadou_home, spec.eval_pack)
        items = _load_eval_items(pack)
        if not items:
            return LevelAssessment(
                level_number=0,
                level_id=spec.id,
                title=spec.title,
                passed=False,
                score_pct=0.0,
                gates=[],
                quests=[{"id": r.id, "text": r.text, "done": False} for r in spec.requirements],
                eval_total=0,
                specialization_id=spec.id,
                branch=spec.branch,
            )

        eval_results = run_eval(items, user_id=user_id)
        metrics = compute_metrics(eval_results, eval_items=items)
        gate_rows = check_gates(spec.gates, metrics)
        passed = bool(gate_rows) and all(g.get("ok") for g in gate_rows)
        ok_count = sum(1 for g in gate_rows if g.get("ok"))
        score_pct = round(ok_count / len(gate_rows), 4) if gate_rows else 0.0
        quests = _quest_status(spec, metrics, gate_rows)
        failures = [ir for ir in eval_results.get("items") or [] if not ir.get("passed")]

        return LevelAssessment(
            level_number=0,
            level_id=spec.id,
            title=spec.title,
            passed=passed,
            score_pct=score_pct,
            gates=gate_rows,
            quests=quests,
            metrics={k: v for k, v in metrics.items() if v is not None},
            eval_total=int(eval_results.get("total") or 0),
            failures=failures,
            specialization_id=spec.id,
            branch=spec.branch,
        )
    finally:
        if prev_home is None:
            os.environ.pop("SHADOU_HOME", None)
        else:
            os.environ["SHADOU_HOME"] = prev_home
