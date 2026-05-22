"""Apply approved FAQ learn proposals into master_faq.md."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from kai.core.faq_markdown import parse_master_faq_schema, render_master_faq_schema
from kai.support_runtime.faq_learn_queue import load_proposal, set_proposal_status

log = logging.getLogger("kai.faq_merge")


def _merge_intent(existing: dict[str, Any] | None, update: dict[str, Any]) -> dict[str, Any]:
    intent_id = (update.get("intent_id") or "").strip()
    if not intent_id:
        raise ValueError("intent_update missing intent_id")

    if existing:
        aliases = list(existing.get("aliases") or [])
        for a in update.get("aliases_add") or []:
            a = str(a).strip()
            if a and a not in aliases:
                aliases.append(a)
        for a in update.get("aliases") or []:
            a = str(a).strip()
            if a and a not in aliases:
                aliases.append(a)
        answer = (existing.get("answer") or "").strip()
        if update.get("answer"):
            answer = str(update["answer"]).strip()
        elif update.get("answer_append"):
            extra = str(update["answer_append"]).strip()
            if extra and extra not in answer:
                answer = f"{answer}\n\n{extra}".strip() if answer else extra
        elif update.get("answer_replace"):
            answer = str(update["answer_replace"]).strip()
        return {"intent_id": intent_id, "aliases": aliases, "answer": answer}

    aliases = [str(a).strip() for a in (update.get("aliases") or []) if str(a).strip()]
    for a in update.get("aliases_add") or []:
        a = str(a).strip()
        if a and a not in aliases:
            aliases.append(a)
    answer = (update.get("answer") or update.get("answer_replace") or "").strip()
    if not answer and update.get("answer_append"):
        answer = str(update["answer_append"]).strip()
    if not answer:
        raise ValueError(f"new intent {intent_id} needs answer or answer_append")
    if not aliases:
        aliases = [intent_id.replace("_", " ")]
    return {"intent_id": intent_id, "aliases": aliases, "answer": answer}


def apply_proposal_json_to_master(
    proposal: dict[str, Any],
    master_path: Path,
) -> dict[str, Any]:
    """Merge proposal.json intent_updates into master_faq.md."""
    raw = master_path.read_text(encoding="utf-8") if master_path.exists() else ""
    schema = parse_master_faq_schema(raw)
    by_id = {row["intent_id"]: row for row in schema.get("intents", [])}

    applied: list[str] = []
    for upd in proposal.get("intent_updates") or []:
        if not isinstance(upd, dict):
            continue
        iid = str(upd.get("intent_id") or "").strip()
        if not iid:
            continue
        merged = _merge_intent(by_id.get(iid), upd)
        by_id[iid] = merged
        applied.append(iid)

    schema["intents"] = list(by_id.values())
    master_path.parent.mkdir(parents=True, exist_ok=True)
    master_path.write_text(render_master_faq_schema(schema), encoding="utf-8")
    return {"ok": True, "intents_applied": applied}


def merge_proposal_into_master(
    proposal_id: str,
    master_path: Path,
    *,
    mark_merged: bool = True,
) -> dict[str, Any]:
    loaded = load_proposal(proposal_id)
    proposal = loaded.get("proposal")
    if not isinstance(proposal, dict):
        return {"ok": False, "error": "missing_proposal_json", "proposal_id": proposal_id}

    out = apply_proposal_json_to_master(proposal, master_path)
    if mark_merged and out.get("ok"):
        set_proposal_status(proposal_id, "merged", note=f"merged into {master_path}")
    out["proposal_id"] = proposal_id
    return out
