"""Copy bundled job-specific training eval packs into a tenant workspace."""

from __future__ import annotations

import shutil
from pathlib import Path

from shadou.training.levels import DEFAULT_JOB_ID, job_id_from_shadou_home, resolve_job_id


def bundled_packs_dir() -> Path:
    return Path(__file__).resolve().parent / "packs"


def ensure_tenant_training_packs(shadou_home: Path, job_id: str | None = None) -> Path:
    """Copy job packs into SHADOU_HOME/eval/training/{job_id}/ if missing."""
    shadou_home = Path(shadou_home).resolve()
    jid = resolve_job_id(job_id or job_id_from_shadou_home(shadou_home))
    dest = shadou_home / "eval" / "training" / jid
    dest.mkdir(parents=True, exist_ok=True)

    src = bundled_packs_dir() / jid
    if src.is_dir():
        for pack in sorted(src.glob("*.jsonl")):
            target = dest / pack.name
            if not target.is_file():
                shutil.copy2(pack, target)
    elif jid == DEFAULT_JOB_ID:
        # Legacy flat bundle at packs/*.jsonl
        flat_src = bundled_packs_dir()
        for pack in sorted(flat_src.glob("level_*.jsonl")) + sorted(flat_src.glob("badge_*.jsonl")):
            target = dest / pack.name
            if not target.is_file():
                shutil.copy2(pack, target)

    return dest


def eval_pack_path(shadou_home: Path, rel: str) -> Path:
    return Path(shadou_home).resolve() / rel
