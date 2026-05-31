"""Tenant-agnostic eval harness for Kai support agents.

Usage:
    python -m kai.tools.eval_run --eval-file PATH [--open-book] [--gates-file PATH]

Eval JSONL schema (one item per line):
    {
        "question": "...",
        "expected_intent": "intent_id or empty",
        "expected_decision": "direct_answer|clarifying_question|escalate_human|abstain",
        "tags": ["critical", ...]   # optional; items tagged "critical" gate the exit code
    }

Exit codes:
    0 — all gates passed (or no critical items failed)
    1 — at least one critical item failed, or a configured gate threshold was missed
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def _load_eval_items(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    items = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                items.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return items


def _load_gates(workspace_yaml_path: Path | None) -> dict[str, float]:
    """Read eval.gates from workspace.yaml, returning a threshold dict."""
    if workspace_yaml_path is None or not workspace_yaml_path.is_file():
        return {}
    try:
        import yaml  # type: ignore[import]
        data = yaml.safe_load(workspace_yaml_path.read_text(encoding="utf-8")) or {}
    except Exception:  # noqa: BLE001
        return {}
    eval_block = data.get("eval") if isinstance(data.get("eval"), dict) else {}
    gates = eval_block.get("gates")
    if not isinstance(gates, dict):
        return {}
    out: dict[str, float] = {}
    for k, v in gates.items():
        try:
            out[str(k)] = float(v)
        except (TypeError, ValueError):
            pass
    return out


def _safe_rate(num: int, den: int) -> float:
    return round(num / den, 4) if den else 0.0


def run_eval(
    eval_items: list[dict[str, Any]],
    *,
    open_book: bool = True,
    user_id: str = "eval_harness",
) -> dict[str, Any]:
    """Run eval against the live runtime. Returns a result dict."""
    if not eval_items:
        return {
            "total": 0,
            "accuracy": None,
            "citation_support_rate": None,
            "abstention_utility": None,
            "per_tag": {},
            "items": [],
        }

    from kai.support_runtime.service import SupportRuntimeService
    from kai.support_runtime.faq_grounding import is_answer_faq_grounded

    svc = SupportRuntimeService()
    svc.startup()

    item_results: list[dict[str, Any]] = []
    total_correct = 0
    total_grounded = 0
    total_direct = 0
    abstain_correct = 0
    abstain_expected = 0
    total_verified_flagged = 0
    total_stale = 0

    for item in eval_items:
        question = str(item.get("question") or "")
        expected_decision = str(item.get("expected_decision") or "")
        expected_intent = str(item.get("expected_intent") or "")
        tags = list(item.get("tags") or [])

        result = svc.execute(text=question, lang="EN", user_id=user_id)

        decision_match = (not expected_decision) or (result.decision == expected_decision)
        intent_match = True
        if expected_intent and result.source_ids:
            intent_match = any(expected_intent in sid for sid in result.source_ids)

        passed = decision_match and intent_match

        observations = ((result.metadata or {}).get("evidence") or {}).get("observations") or []
        grounded = is_answer_faq_grounded(
            answer=result.answer,
            user_text=question,
            source_ids=result.source_ids,
            observations=observations,
        )

        verification = (result.metadata or {}).get("verification") or {}
        verification_flagged = bool(verification.get("flagged"))
        stale_evidence = bool((result.metadata or {}).get("stale_evidence"))

        if passed:
            total_correct += 1
        if result.decision == "direct_answer":
            total_direct += 1
            if grounded:
                total_grounded += 1
        if expected_decision == "abstain":
            abstain_expected += 1
            if result.decision == "abstain":
                abstain_correct += 1
        if verification_flagged:
            total_verified_flagged += 1
        if stale_evidence:
            total_stale += 1

        item_results.append({
            "question": question,
            "expected_decision": expected_decision,
            "actual_decision": result.decision,
            "expected_intent": expected_intent,
            "grounded": grounded,
            "passed": passed,
            "tags": tags,
            "confidence": result.confidence,
            "evidence_count": len(result.evidence_ledger),
            "verification_flagged": verification_flagged,
            "stale_evidence": stale_evidence,
        })

    total = len(eval_items)

    # Per-tag breakdown
    all_tags: set[str] = set()
    for ir in item_results:
        all_tags.update(ir.get("tags") or [])

    per_tag: dict[str, dict[str, Any]] = {}
    for tag in sorted(all_tags):
        tagged = [ir for ir in item_results if tag in (ir.get("tags") or [])]
        t_total = len(tagged)
        t_correct = sum(1 for ir in tagged if ir["passed"])
        per_tag[tag] = {
            "total": t_total,
            "correct": t_correct,
            "accuracy": _safe_rate(t_correct, t_total),
        }

    return {
        "total": total,
        "accuracy": _safe_rate(total_correct, total),
        "citation_support_rate": _safe_rate(total_grounded, total_direct) if total_direct else None,
        "abstention_utility": _safe_rate(abstain_correct, abstain_expected) if abstain_expected else None,
        "verification_flag_rate": _safe_rate(total_verified_flagged, total),
        "stale_citation_rate": _safe_rate(total_stale, total),
        "per_tag": per_tag,
        "items": item_results,
    }


def _check_gates(results: dict[str, Any], gates: dict[str, float]) -> list[str]:
    """Return list of gate failure messages.

    Gate keys that look like ``accuracy_<tag>`` are resolved against
    ``per_tag.<tag>.accuracy`` in the results dict.
    """
    failures: list[str] = []
    per_tag: dict[str, Any] = results.get("per_tag") or {}
    for metric, threshold in gates.items():
        # Check per-tag shorthand first: "accuracy_critical" → per_tag["critical"]["accuracy"]
        if metric.startswith("accuracy_"):
            tag = metric[len("accuracy_"):]
            tag_data = per_tag.get(tag)
            if tag_data is not None:
                value = tag_data.get("accuracy")
                if value is not None and float(value) < threshold:
                    failures.append(f"{metric}: {value:.4f} < {threshold:.4f}")
                continue
        value = results.get(metric)
        if value is None:
            continue
        if float(value) < threshold:
            failures.append(f"{metric}: {value:.4f} < {threshold:.4f}")
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Kai eval harness")
    parser.add_argument("--eval-file", required=True, help="Path to eval JSONL")
    parser.add_argument("--open-book", action="store_true", default=True, help="Use live runtime tools (default)")
    parser.add_argument("--workspace-yaml", default=None, help="workspace.yaml for gate config")
    parser.add_argument("--output", default=None, help="Write JSON results to file")
    args = parser.parse_args(argv)

    eval_path = Path(args.eval_file)
    items = _load_eval_items(eval_path)

    workspace_yaml_path: Path | None = None
    if args.workspace_yaml:
        workspace_yaml_path = Path(args.workspace_yaml)
    else:
        try:
            from kai.workspace.manifest import workspace_yaml_path as _wsp
            workspace_yaml_path = _wsp()
        except Exception:  # noqa: BLE001
            pass

    gates = _load_gates(workspace_yaml_path)

    results = run_eval(items, open_book=args.open_book)

    print(json.dumps({k: v for k, v in results.items() if k != "items"}, indent=2))

    if args.output:
        Path(args.output).write_text(json.dumps(results, indent=2), encoding="utf-8")

    if results["total"] == 0:
        return 0

    gate_failures = _check_gates(results, gates)

    critical_tag = results.get("per_tag", {}).get("critical", {})
    critical_failures = [ir for ir in results["items"] if "critical" in (ir.get("tags") or []) and not ir["passed"]]

    if critical_failures:
        print(f"\nCRITICAL FAILURES ({len(critical_failures)}):", file=sys.stderr)
        for ir in critical_failures:
            print(f"  [{ir['actual_decision']}] {ir['question'][:80]}", file=sys.stderr)

    if gate_failures:
        print(f"\nGATE FAILURES:", file=sys.stderr)
        for f in gate_failures:
            print(f"  {f}", file=sys.stderr)

    if critical_failures or gate_failures:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
