#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shadou.support_runtime.service import SupportRuntimeService


def _safe_rate(num: int, den: int) -> float:
    return round((num / den) * 100.0, 2) if den else 0.0


def run_eval(dataset_path: Path) -> dict:
    svc = SupportRuntimeService()
    svc.startup()

    rows = [json.loads(line) for line in dataset_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    total = len(rows)
    correct_intent = 0
    correct_decision = 0
    unnecessary_escalations = 0
    unnecessary_tool = 0
    grounded_with_sources = 0

    for row in rows:
        query = row.get("query", "")
        expected_decision = row.get("expected_decision")
        expected_capability = row.get("expected_capability")
        out = svc.execute(query, lang=row.get("lang", "EN"))

        if expected_decision and out.decision == expected_decision:
            correct_decision += 1
        if expected_capability and out.capability_used == expected_capability:
            correct_intent += 1
        if row.get("tool_required") is False and out.tool_needed:
            unnecessary_tool += 1
        if row.get("escalation_required") is False and out.escalate_needed:
            unnecessary_escalations += 1
        if out.decision == "direct_answer" and out.source_ids:
            grounded_with_sources += 1

    return {
        "total": total,
        "decision_accuracy_pct": _safe_rate(correct_decision, total),
        "intent_proxy_accuracy_pct": _safe_rate(correct_intent, total),
        "grounded_answer_with_sources_pct": _safe_rate(grounded_with_sources, total),
        "unnecessary_tool_calls": unnecessary_tool,
        "unnecessary_escalations": unnecessary_escalations,
    }


def main() -> None:
    dataset = Path("tools/eval_dataset.jsonl")
    if not dataset.exists():
        raise SystemExit("Missing tools/eval_dataset.jsonl")
    summary = run_eval(dataset)
    print(json.dumps(summary, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
