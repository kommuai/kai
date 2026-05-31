"""Assess core training levels and specialization badges for a tenant workspace."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from shadou.training.levels import (
    job_id_from_training_block,
    load_levels,
    load_specializations,
    max_core_level,
    resolve_job_id,
)
from shadou.training.score_level import assess_level, assess_specialization


def _read_training_block(shadou_home: Path) -> dict[str, Any]:
    import yaml

    ws = shadou_home / "workspace.yaml"
    if not ws.is_file():
        return {}
    data = yaml.safe_load(ws.read_text(encoding="utf-8")) or {}
    t = data.get("training")
    return t if isinstance(t, dict) else {}


def _write_training_block(shadou_home: Path, patch: dict[str, Any]) -> None:
    import yaml

    ws = shadou_home / "workspace.yaml"
    if not ws.is_file():
        return
    data = yaml.safe_load(ws.read_text(encoding="utf-8")) or {}
    training = data.get("training") if isinstance(data.get("training"), dict) else {}
    training.update(patch)
    data["training"] = training
    ws.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False), encoding="utf-8")


def assess_agent(
    shadou_home: Path,
    *,
    job_id: str | None = None,
    max_level: int | None = None,
    include_badges: bool = True,
    user_id: str = "training_harness",
) -> dict[str, Any]:
    """Run core level assessments; current_level = highest passed. Optionally assess badges."""
    shadou_home = Path(shadou_home).resolve()
    cap = max_level if max_level is not None else max_core_level()
    levels = tuple(lv for lv in load_levels() if lv.number <= cap)

    level_results: dict[int, dict[str, Any]] = {}
    current_level = 0
    current_title = ""
    current_emoji = ""

    for lv in levels:
        assessment = assess_level(shadou_home, lv.number, job_id=jid, user_id=user_id)
        level_results[lv.number] = assessment.to_dict()
        if assessment.passed and lv.number > current_level:
            current_level = lv.number
            current_title = lv.title
            current_emoji = lv.emoji

    max_lv = max_core_level()
    next_level = current_level + 1 if current_level < max_lv else None
    progress_to_next = 0.0
    if next_level is not None:
        nxt = level_results.get(next_level)
        if nxt:
            progress_to_next = float(nxt.get("score_pct") or 0.0)

    badge_results: dict[str, dict[str, Any]] = {}
    earned_badges: list[str] = []
    if include_badges:
        for spec in load_specializations(jid):
            if current_level < spec.prereq_level:
                badge_results[spec.id] = {
                    "specialization_id": spec.id,
                    "branch": spec.branch,
                    "title": spec.title,
                    "passed": False,
                    "score_pct": 0.0,
                    "locked": True,
                    "lock_reason": f"Requires core level {spec.prereq_level}",
                }
                continue
            assessment = assess_specialization(shadou_home, spec.id, user_id=user_id)
            badge_results[spec.id] = assessment.to_dict()
            if assessment.passed:
                earned_badges.append(spec.id)

    now = datetime.now(timezone.utc).isoformat()
    summary = {
        "agent_job": jid,
        "current_level": current_level,
        "current_level_title": current_title,
        "current_level_emoji": current_emoji,
        "next_level": next_level,
        "progress_to_next": progress_to_next,
        "assessed_at": now,
        "level_results": level_results,
        "badge_results": badge_results,
        "earned_badges": earned_badges,
    }

    _write_training_block(
        shadou_home,
        {
            "agent_job": jid,
            "current_level": current_level,
            "current_level_title": current_title,
            "current_level_emoji": current_emoji,
            "earned_badges": earned_badges,
            "last_assessed_at": now,
        },
    )

    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Assess Shadou agent training levels and badges")
    parser.add_argument("--shadou-home", required=True, help="Tenant workspace path (SHADOU_HOME)")
    parser.add_argument("--level", type=int, default=None, help="Assess only this core level (1-3)")
    parser.add_argument(
        "--specialization",
        default=None,
        help="Assess only this specialization id (e.g. deal_whisperer)",
    )
    parser.add_argument("--json-out", default=None, help="Write JSON results to file")
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Emit single-line JSON on stdout (for Studio subprocess)",
    )
    parser.add_argument(
        "--no-badges",
        action="store_true",
        help="Skip specialization badge assessments on full run",
    )
    args = parser.parse_args(argv)

    shadou_home = Path(args.shadou_home)
    os.environ["SHADOU_HOME"] = str(shadou_home.resolve())

    training = _read_training_block(shadou_home)
    jid = job_id_from_training_block(training)

    if args.specialization:
        result = assess_specialization(shadou_home, args.specialization, job_id=jid).to_dict()
    elif args.level is not None:
        result = assess_level(shadou_home, args.level, job_id=jid).to_dict()
    else:
        result = assess_agent(shadou_home, job_id=jid, include_badges=not args.no_badges)

    if args.compact:
        print(json.dumps(result))
    else:
        print(json.dumps(result, indent=2))
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(result, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
