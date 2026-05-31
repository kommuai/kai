"""Load job-specific core levels and specialization definitions from levels.yaml."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

DEFAULT_JOB_ID = "customer_support"


@dataclass(frozen=True)
class JobDef:
    id: str
    label: str
    description: str


@dataclass(frozen=True)
class LevelRequirement:
    id: str
    text: str


@dataclass(frozen=True)
class LevelDef:
    id: str
    number: int
    title: str
    tagline: str
    emoji: str
    color: str
    meaning: str
    eval_pack: str
    requirements: tuple[LevelRequirement, ...]
    gates: dict[str, float]
    scorers: tuple[str, ...]
    job_id: str


@dataclass(frozen=True)
class SpecializationDef:
    id: str
    branch: str
    title: str
    tagline: str
    emoji: str
    color: str
    prereq_level: int
    meaning: str
    eval_pack: str
    requirements: tuple[LevelRequirement, ...]
    gates: dict[str, float]
    scorers: tuple[str, ...]
    job_id: str


def _levels_yaml_path() -> Path:
    return Path(__file__).resolve().parent / "levels.yaml"


def _parse_requirements(row: dict[str, Any]) -> tuple[LevelRequirement, ...]:
    reqs: list[LevelRequirement] = []
    for r in row.get("requirements") or []:
        if isinstance(r, dict) and r.get("id"):
            reqs.append(LevelRequirement(id=str(r["id"]), text=str(r.get("text") or "")))
    return tuple(reqs)


def _parse_gates(row: dict[str, Any]) -> dict[str, float]:
    gates_raw = row.get("gates") or {}
    gates: dict[str, float] = {}
    if isinstance(gates_raw, dict):
        for k, v in gates_raw.items():
            try:
                gates[str(k)] = float(v)
            except (TypeError, ValueError):
                pass
    return gates


def _parse_scorers(row: dict[str, Any]) -> tuple[str, ...]:
    scorers = row.get("scorers") or []
    if isinstance(scorers, str):
        scorers = [scorers]
    return tuple(str(s) for s in scorers)


@lru_cache(maxsize=1)
def _load_yaml_jobs() -> dict[str, dict[str, Any]]:
    import yaml

    raw = yaml.safe_load(_levels_yaml_path().read_text(encoding="utf-8")) or {}
    jobs = raw.get("jobs")
    if isinstance(jobs, dict) and jobs:
        return {str(k): v for k, v in jobs.items() if isinstance(v, dict)}
    # Legacy flat file → customer_support only
    if raw.get("levels"):
        return {
            DEFAULT_JOB_ID: {
                "label": "Customer Support",
                "description": "Customer-facing support",
                "levels": raw.get("levels") or [],
                "specializations": raw.get("specializations") or [],
            }
        }
    return {}


def list_jobs() -> tuple[JobDef, ...]:
    out: list[JobDef] = []
    for job_id, block in sorted(_load_yaml_jobs().items()):
        out.append(
            JobDef(
                id=job_id,
                label=str(block.get("label") or job_id),
                description=str(block.get("description") or "").strip(),
            )
        )
    return tuple(out)


def resolve_job_id(job_id: str | None) -> str:
    jid = (job_id or "").strip() or DEFAULT_JOB_ID
    if jid in _load_yaml_jobs():
        return jid
    return DEFAULT_JOB_ID


def job_id_from_training_block(training: dict[str, Any] | None) -> str:
    if not training:
        return DEFAULT_JOB_ID
    return resolve_job_id(str(training.get("agent_job") or training.get("job") or ""))


def job_id_from_shadou_home(shadou_home: Path) -> str:
    import yaml

    ws = Path(shadou_home) / "workspace.yaml"
    if not ws.is_file():
        return DEFAULT_JOB_ID
    data = yaml.safe_load(ws.read_text(encoding="utf-8")) or {}
    t = data.get("training")
    return job_id_from_training_block(t if isinstance(t, dict) else None)


def get_job(job_id: str | None = None) -> JobDef | None:
    jid = resolve_job_id(job_id)
    block = _load_yaml_jobs().get(jid)
    if not block:
        return None
    return JobDef(id=jid, label=str(block.get("label") or jid), description=str(block.get("description") or ""))


def load_levels(job_id: str | None = None) -> tuple[LevelDef, ...]:
    jid = resolve_job_id(job_id)
    block = _load_yaml_jobs().get(jid) or {}
    items = block.get("levels") or []
    out: list[LevelDef] = []
    for row in items:
        if not isinstance(row, dict):
            continue
        out.append(
            LevelDef(
                id=str(row.get("id") or f"level_{row.get('number')}"),
                number=int(row.get("number") or 0),
                title=str(row.get("title") or ""),
                tagline=str(row.get("tagline") or ""),
                emoji=str(row.get("emoji") or ""),
                color=str(row.get("color") or "#6366f1"),
                meaning=str(row.get("meaning") or "").strip(),
                eval_pack=str(row.get("eval_pack") or ""),
                requirements=_parse_requirements(row),
                gates=_parse_gates(row),
                scorers=_parse_scorers(row),
                job_id=jid,
            )
        )
    return tuple(sorted(out, key=lambda x: x.number))


def load_specializations(job_id: str | None = None) -> tuple[SpecializationDef, ...]:
    jid = resolve_job_id(job_id)
    block = _load_yaml_jobs().get(jid) or {}
    items = block.get("specializations") or []
    out: list[SpecializationDef] = []
    for row in items:
        if not isinstance(row, dict):
            continue
        out.append(
            SpecializationDef(
                id=str(row.get("id") or ""),
                branch=str(row.get("branch") or ""),
                title=str(row.get("title") or ""),
                tagline=str(row.get("tagline") or ""),
                emoji=str(row.get("emoji") or ""),
                color=str(row.get("color") or "#6366f1"),
                prereq_level=int(row.get("prereq_level") or 3),
                meaning=str(row.get("meaning") or "").strip(),
                eval_pack=str(row.get("eval_pack") or ""),
                requirements=_parse_requirements(row),
                gates=_parse_gates(row),
                scorers=_parse_scorers(row),
                job_id=jid,
            )
        )
    return tuple(out)


def get_level(number: int, job_id: str | None = None) -> LevelDef | None:
    for lv in load_levels(job_id):
        if lv.number == number:
            return lv
    return None


def get_specialization(spec_id: str, job_id: str | None = None) -> SpecializationDef | None:
    for sp in load_specializations(job_id):
        if sp.id == spec_id:
            return sp
    return None


def max_core_level(job_id: str | None = None) -> int:
    levels = load_levels(job_id)
    return max((lv.number for lv in levels), default=3)


def jobs_dict_for_api() -> list[dict[str, Any]]:
    return [
        {"id": j.id, "label": j.label, "description": j.description}
        for j in list_jobs()
    ]


def levels_dict_for_api(job_id: str | None = None) -> list[dict[str, Any]]:
    return [
        {
            "id": lv.id,
            "number": lv.number,
            "title": lv.title,
            "tagline": lv.tagline,
            "emoji": lv.emoji,
            "color": lv.color,
            "meaning": lv.meaning,
            "requirements": [{"id": r.id, "text": r.text} for r in lv.requirements],
            "gates": lv.gates,
        }
        for lv in load_levels(job_id)
    ]


def specializations_dict_for_api(job_id: str | None = None) -> list[dict[str, Any]]:
    return [
        {
            "id": sp.id,
            "branch": sp.branch,
            "title": sp.title,
            "tagline": sp.tagline,
            "emoji": sp.emoji,
            "color": sp.color,
            "prereq_level": sp.prereq_level,
            "meaning": sp.meaning,
            "requirements": [{"id": r.id, "text": r.text} for r in sp.requirements],
            "gates": sp.gates,
        }
        for sp in load_specializations(job_id)
    ]
