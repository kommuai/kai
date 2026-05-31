"""FAQ learn queue — one directory per proposal (Phase 2, Hermes-style review before merge)."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from shadou.settings import get_settings


def learn_queue_root() -> Path:
    s = get_settings()
    p = Path(s.faq_learn_queue_dir)
    if not p.is_absolute():
        p = s.base_dir / p
    p.mkdir(parents=True, exist_ok=True)
    return p


def _user_slug(user_id: str) -> str:
    return hashlib.sha256((user_id or "unknown").encode()).hexdigest()[:12]


def make_proposal_id(user_id: str, trigger: str) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{ts}_{_user_slug(user_id)}_{trigger}"


def proposal_dir(proposal_id: str) -> Path:
    safe = re.sub(r"[^a-zA-Z0-9_\-]", "_", proposal_id)[:120]
    return learn_queue_root() / safe


def write_proposal(
    proposal_id: str,
    *,
    meta: dict[str, Any],
    transcript: str,
    diff_text: str = "",
    proposal: dict[str, Any] | None = None,
) -> Path:
    d = proposal_dir(proposal_id)
    d.mkdir(parents=True, exist_ok=True)
    (d / "meta.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (d / "transcript.txt").write_text((transcript or "").strip() + "\n", encoding="utf-8")
    if diff_text.strip():
        (d / "proposal.diff").write_text(diff_text.rstrip() + "\n", encoding="utf-8")
    if proposal:
        (d / "proposal.json").write_text(
            json.dumps(proposal, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    return d


def list_proposals(*, status: str | None = "pending") -> list[dict[str, Any]]:
    root = learn_queue_root()
    out: list[dict[str, Any]] = []
    for child in sorted(root.iterdir()):
        if not child.is_dir():
            continue
        meta_path = child / "meta.json"
        if not meta_path.exists():
            continue
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        meta["proposal_id"] = child.name
        meta["path"] = str(child)
        if status and meta.get("status") != status:
            continue
        out.append(meta)
    return out


def load_proposal(proposal_id: str) -> dict[str, Any]:
    d = proposal_dir(proposal_id)
    if not d.is_dir():
        raise FileNotFoundError(proposal_id)
    meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
    meta["proposal_id"] = proposal_id
    meta["path"] = str(d)
    if (d / "transcript.txt").exists():
        meta["transcript"] = (d / "transcript.txt").read_text(encoding="utf-8")
    if (d / "proposal.diff").exists():
        meta["diff"] = (d / "proposal.diff").read_text(encoding="utf-8")
    if (d / "proposal.json").exists():
        meta["proposal"] = json.loads((d / "proposal.json").read_text(encoding="utf-8"))
    return meta


def set_proposal_status(proposal_id: str, status: str, *, note: str = "") -> None:
    d = proposal_dir(proposal_id)
    meta_path = d / "meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["status"] = status
    meta["status_updated_at"] = datetime.now(timezone.utc).isoformat()
    if note:
        meta["status_note"] = note
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
