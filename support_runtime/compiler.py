from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
import re

from config import AGENT_WORKSPACE, resolve_master_faq_path
from core.faq_markdown import parse_master_faq_schema


COMPILED_DIR = Path(AGENT_WORKSPACE) / "compiled"
INTENTS_PATH = COMPILED_DIR / "intents.json"
WORKFLOWS_PATH = COMPILED_DIR / "workflows.json"
CHUNKS_PATH = COMPILED_DIR / "kb_chunks.jsonl"
TOOLS_PATH = COMPILED_DIR / "tool_policies.json"


def _slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return s[:80] or "intent"


def _parse_iso_date(value: str | None) -> date | None:
    s = (value or "").strip()
    if not s:
        return None
    try:
        return datetime.strptime(s[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def _infer_route_type(question: str) -> str:
    q = question.lower()
    if any(k in q for k in ("order", "shipment", "payment", "tracking")):
        return "account_order_status_intent"
    if any(k in q for k in ("error", "not working", "cannot", "can't", "troubleshoot", "issue")):
        return "troubleshooting_intent"
    return "known_faq_intent"


def compile_canonical_knowledge() -> dict[str, int]:
    COMPILED_DIR.mkdir(parents=True, exist_ok=True)
    faq_path = Path(resolve_master_faq_path())
    raw = faq_path.read_text(encoding="utf-8") if faq_path.exists() else ""
    parsed = parse_master_faq_schema(raw)

    intents = []
    chunks = []
    workflows = {"troubleshooting": [], "clarifying": [], "escalation": [], "custom": []}
    tool_policies = {
        "order_status": {"required_entities": ["order_id"], "tool_name": "order_status_lookup"},
        "shipment_tracking": {"required_entities": ["tracking_id"], "tool_name": "shipment_tracking_lookup"},
        "payment_verification": {"required_entities": ["payment_ref"], "tool_name": "payment_verification_lookup"},
    }

    for idx, row in enumerate(parsed.get("intents", []), start=1):
        intent_id = (row.get("intent_id") or "").strip()
        aliases = row.get("aliases") or []
        answer = (row.get("answer") or "").strip()
        if not intent_id or not answer:
            continue
        question = aliases[0] if aliases else intent_id.replace("_", " ")
        route_type = _infer_route_type(question)
        intents.append(
            {
                "intent_id": intent_id,
                "route_type": route_type,
                "aliases": aliases if aliases else [question.lower(), re.sub(r"[^a-z0-9 ]+", " ", question.lower()).strip()],
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
        chunk_text = "\n".join(lines).strip()
        if len(lines) <= 2:
            continue
        chunks.append(
            {
                "source_id": f"dynamic:{dname}",
                "text": chunk_text,
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
    workflows["escalation"].append(
        {
            "trigger": "low_confidence_or_unsafe",
            "action": "handover_human",
            "notes": "Preserve chatwoot handover semantics.",
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

    INTENTS_PATH.write_text(json.dumps(intents, indent=2, ensure_ascii=True), encoding="utf-8")
    WORKFLOWS_PATH.write_text(json.dumps(workflows, indent=2, ensure_ascii=True), encoding="utf-8")
    TOOLS_PATH.write_text(json.dumps(tool_policies, indent=2, ensure_ascii=True), encoding="utf-8")
    with CHUNKS_PATH.open("w", encoding="utf-8") as fh:
        for item in chunks:
            fh.write(json.dumps(item, ensure_ascii=True) + "\n")

    return {"intents": len(intents), "chunks": len(chunks), "dynamic_chunks": sum(1 for c in chunks if str(c.get("source_id", "")).startswith("dynamic:"))}
