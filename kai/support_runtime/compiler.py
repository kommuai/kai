from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
import re

from kai.settings import get_settings
from kai.core.faq_markdown import parse_master_faq_schema


def _compiled_dir() -> Path:
    try:
        from kai.workspace.manifest import load_workspace_manifest

        manifest = load_workspace_manifest()
        return get_settings().kai_home / manifest.paths.knowledge_compiled_dir
    except Exception:  # noqa: BLE001
        return get_settings().kai_home / "compiled"


def _parse_iso_date(value: str | None) -> date | None:
    s = (value or "").strip()
    if not s:
        return None
    try:
        return datetime.strptime(s[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def _chunk_category(question: str) -> str:
    q = question.lower()
    if any(k in q for k in ("error", "not working", "cannot", "can't", "troubleshoot", "issue")):
        return "troubleshooting_intent"
    if any(k in q for k in ("order", "shipment", "payment", "tracking")):
        return "account_order_status_intent"
    return "known_faq_intent"


def _write_extra_artifacts(
    compiled_dir: Path,
    parsed: dict,
    *,
    intent_rows: list[dict],
) -> None:
    """Optional debug artifacts (off by default). Not read by production runtime."""
    intents = []
    workflows: dict = {"troubleshooting": [], "clarifying": [], "escalation": [], "custom": []}
    tool_policies = {
        "order_status": {"required_entities": ["order_id"], "tool_name": "order_status_lookup"},
        "shipment_tracking": {"required_entities": ["tracking_id"], "tool_name": "shipment_tracking_lookup"},
        "payment_verification": {"required_entities": ["payment_ref"], "tool_name": "payment_verification_lookup"},
    }
    for idx, row in enumerate(intent_rows, start=1):
        intent_id = row["intent_id"]
        question = row["question"]
        answer = row["answer"]
        route_type = _chunk_category(question)
        intents.append(
            {
                "intent_id": intent_id,
                "route_type": route_type,
                "aliases": row["aliases"],
                "canonical_answer": answer,
                "policy_flags": ["grounded_only"],
                "confidence_threshold": 0.75 if route_type == "known_faq_intent" else 0.62,
                "metadata": {
                    "source": "master_faq",
                    "index": idx,
                    "product": "KA",
                    "audience": "customer",
                    "version": "v1",
                    "recency": "current",
                },
            }
        )
        if route_type == "troubleshooting_intent":
            workflows["troubleshooting"].append(
                {
                    "intent_id": intent_id,
                    "steps": [
                        "Acknowledge issue and restate problem.",
                        "Ask for key identifiers if missing.",
                        "Provide canonical troubleshooting actions.",
                        "Escalate when unresolved.",
                    ],
                }
            )
    workflows["escalation"].append(
        {
            "trigger": "low_confidence_or_unsafe",
            "action": "handover_human",
            "notes": "Preserve human handover semantics.",
        }
    )
    for wf in parsed.get("workflows", []):
        workflows["custom"].append(
            {
                "workflow_id": wf.get("workflow_id"),
                "steps": wf.get("steps") or [],
            }
        )
    tool_policies["reference_data"] = {
        "data": parsed.get("data", []),
        "dynamic": parsed.get("dynamic", []),
    }
    (compiled_dir / "intents.json").write_text(
        json.dumps(intents, indent=2, ensure_ascii=True), encoding="utf-8"
    )
    (compiled_dir / "workflows.json").write_text(
        json.dumps(workflows, indent=2, ensure_ascii=True), encoding="utf-8"
    )
    (compiled_dir / "tool_policies.json").write_text(
        json.dumps(tool_policies, indent=2, ensure_ascii=True), encoding="utf-8"
    )


def compile_canonical_knowledge() -> dict[str, int]:
    """Compile master_faq.md → kb_chunks.jsonl (runtime retrieval). Optional extra JSON for debug."""
    compiled_dir = _compiled_dir()
    compiled_dir.mkdir(parents=True, exist_ok=True)
    faq_path = get_settings().resolve_master_faq_path()
    raw = faq_path.read_text(encoding="utf-8") if faq_path.exists() else ""
    parsed = parse_master_faq_schema(raw)

    chunks: list[dict] = []
    intent_rows: list[dict] = []
    intent_count = 0

    for row in parsed.get("intents", []):
        intent_id = (row.get("intent_id") or "").strip()
        aliases = row.get("aliases") or []
        answer = (row.get("answer") or "").strip()
        if not intent_id or not answer:
            continue
        question = aliases[0] if aliases else intent_id.replace("_", " ")
        route_type = _chunk_category(question)
        intent_count += 1
        intent_rows.append(
            {
                "intent_id": intent_id,
                "question": question,
                "answer": answer,
                "aliases": aliases if aliases else [question.lower()],
            }
        )
        chunks.append(
            {
                "source_id": f"faq:{intent_id}",
                "text": f"Q: {question}\nA: {answer}",
                "metadata": {
                    "category": route_type,
                    "intent_id": intent_id,
                    "source": "master_faq",
                    "product": "KA",
                    "audience": "customer",
                    "version": "v1",
                },
            }
        )

    today = date.today()
    skip_dyn_fields = {"valid_from", "valid_until", "priority"}
    for dyn in parsed.get("dynamic", []):
        dname = (dyn.get("name") or "").strip()
        fields = dyn.get("fields") or {}
        if not dname or not isinstance(fields, dict):
            continue
        vf = _parse_iso_date(str(dyn.get("valid_from") or fields.get("valid_from") or ""))
        vu = _parse_iso_date(str(dyn.get("valid_until") or fields.get("valid_until") or ""))
        if vu and today > vu:
            continue
        if vf and today < vf:
            continue
        try:
            priority = int(dyn.get("priority", fields.get("priority", 0)))
        except (TypeError, ValueError):
            priority = 0
        lines = [f"Q: dynamic {dname} (current operational status)", "A:"]
        for fk, fv in sorted(fields.items()):
            if fk in skip_dyn_fields:
                continue
            lines.append(f"{fk}: {fv}")
        if len(lines) <= 2:
            continue
        chunks.append(
            {
                "source_id": f"dynamic:{dname}",
                "text": "\n".join(lines).strip(),
                "metadata": {
                    "category": "dynamic_faq",
                    "source": "dynamic_faq",
                    "dynamic_name": dname,
                    "dynamic_priority": priority,
                    "product": "KA",
                    "audience": "customer",
                    "version": "v1",
                },
            }
        )

    chunks_path = compiled_dir / "kb_chunks.jsonl"
    with chunks_path.open("w", encoding="utf-8") as fh:
        for item in chunks:
            fh.write(json.dumps(item, ensure_ascii=True) + "\n")

    dynamic_count = sum(1 for c in chunks if str(c.get("source_id", "")).startswith("dynamic:"))
    _write_corpus_map(compiled_dir, intent_rows=intent_rows, dynamic_count=dynamic_count, total_chunks=len(chunks))

    if get_settings().kai_compile_extra_artifacts:
        _write_extra_artifacts(compiled_dir, parsed, intent_rows=intent_rows)

    return {
        "intents": intent_count,
        "chunks": len(chunks),
        "dynamic_chunks": dynamic_count,
    }


def _write_corpus_map(
    compiled_dir: "Path",
    *,
    intent_rows: list[dict],
    dynamic_count: int,
    total_chunks: int,
) -> None:
    """Write corpus_map.json — deterministic index of compiled knowledge."""
    intents = [
        {
            "intent_id": row["intent_id"],
            "title": row["aliases"][0] if row.get("aliases") else row["intent_id"].replace("_", " "),
            "aliases": row.get("aliases") or [],
            "chunk_count": 1,
        }
        for row in intent_rows
    ]
    corpus_map = {
        "schema_version": 1,
        "compiled_at": str(date.today()),
        "source": "master_faq",
        "intents": intents,
        "dynamic_item_count": dynamic_count,
        "total_chunks": total_chunks,
    }
    map_path = compiled_dir / "corpus_map.json"
    map_path.write_text(json.dumps(corpus_map, indent=2, ensure_ascii=True), encoding="utf-8")
