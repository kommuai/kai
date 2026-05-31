"""Eval comparison tool for Shadou — compare baseline vs candidate eval results.

Usage:
    python -m shadou.tools.eval_compare --baseline results_v1.json --candidate results_v2.json

Exit codes:
    0 — no critical regression
    1 — accuracy_critical regressed, or any configured critical gate failed

Inputs are JSON files produced by ``shadou.tools.eval_run`` (with ``--output PATH``).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


_REGRESSION_METRICS = ("accuracy", "citation_support_rate", "abstention_utility")
_CRITICAL_METRIC = "accuracy_critical"


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Result file not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _safe_delta(candidate: float | None, baseline: float | None) -> float | None:
    if candidate is None or baseline is None:
        return None
    return round(candidate - baseline, 4)


def _tag_accuracy(results: dict[str, Any], tag: str) -> float | None:
    return (results.get("per_tag") or {}).get(tag, {}).get("accuracy")


def compare(baseline: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    """Return a structured diff between two eval result dicts."""
    metric_deltas: dict[str, Any] = {}
    for metric in _REGRESSION_METRICS:
        delta = _safe_delta(candidate.get(metric), baseline.get(metric))
        metric_deltas[metric] = {
            "baseline": baseline.get(metric),
            "candidate": candidate.get(metric),
            "delta": delta,
            "regressed": (delta is not None and delta < 0),
        }

    # Per-tag accuracy deltas
    all_tags = set((baseline.get("per_tag") or {}).keys()) | set((candidate.get("per_tag") or {}).keys())
    tag_deltas: dict[str, Any] = {}
    for tag in sorted(all_tags):
        b_acc = _tag_accuracy(baseline, tag)
        c_acc = _tag_accuracy(candidate, tag)
        delta = _safe_delta(c_acc, b_acc)
        tag_deltas[tag] = {
            "baseline_accuracy": b_acc,
            "candidate_accuracy": c_acc,
            "delta": delta,
            "regressed": (delta is not None and delta < 0),
        }

    # Item-level comparison (requires "items" in both)
    b_items = {i["question"]: i for i in (baseline.get("items") or [])}
    c_items = {i["question"]: i for i in (candidate.get("items") or [])}

    new_failures: list[str] = []
    fixed_items: list[str] = []
    for q, b_item in b_items.items():
        c_item = c_items.get(q)
        if c_item is None:
            continue
        if b_item.get("passed") and not c_item.get("passed"):
            new_failures.append(q)
        elif not b_item.get("passed") and c_item.get("passed"):
            fixed_items.append(q)

    critical_regressed = (
        tag_deltas.get("critical", {}).get("regressed", False)
        or metric_deltas.get("accuracy", {}).get("regressed", False)
    )

    return {
        "metrics": metric_deltas,
        "per_tag": tag_deltas,
        "new_failures": new_failures,
        "fixed_items": fixed_items,
        "critical_regressed": critical_regressed,
        "summary": {
            "baseline_total": baseline.get("total"),
            "candidate_total": candidate.get("total"),
            "new_failures_count": len(new_failures),
            "fixed_items_count": len(fixed_items),
        },
    }


def _print_report(diff: dict[str, Any]) -> None:
    print("\n=== Eval Comparison Report ===")
    summary = diff["summary"]
    print(f"Baseline: {summary['baseline_total']} items | Candidate: {summary['candidate_total']} items")

    print("\nMetric deltas:")
    for metric, data in diff["metrics"].items():
        sign = "▼" if data["regressed"] else ("▲" if (data["delta"] or 0) > 0 else "—")
        b = f"{data['baseline']:.4f}" if data["baseline"] is not None else "N/A"
        c = f"{data['candidate']:.4f}" if data["candidate"] is not None else "N/A"
        d = f"{data['delta']:+.4f}" if data["delta"] is not None else "N/A"
        print(f"  {sign} {metric}: {b} → {c} ({d})")

    if diff["per_tag"]:
        print("\nPer-tag accuracy:")
        for tag, data in diff["per_tag"].items():
            sign = "▼" if data["regressed"] else ("▲" if (data["delta"] or 0) > 0 else "—")
            b = f"{data['baseline_accuracy']:.4f}" if data["baseline_accuracy"] is not None else "N/A"
            c = f"{data['candidate_accuracy']:.4f}" if data["candidate_accuracy"] is not None else "N/A"
            d = f"{data['delta']:+.4f}" if data["delta"] is not None else "N/A"
            print(f"  {sign} [{tag}]: {b} → {c} ({d})")

    if diff["new_failures"]:
        print(f"\nNew failures ({len(diff['new_failures'])}):")
        for q in diff["new_failures"][:10]:
            print(f"  ✗ {q[:80]}")
        if len(diff["new_failures"]) > 10:
            print(f"  ... and {len(diff['new_failures']) - 10} more")

    if diff["fixed_items"]:
        print(f"\nFixed items ({len(diff['fixed_items'])}):")
        for q in diff["fixed_items"][:10]:
            print(f"  ✓ {q[:80]}")

    if diff["critical_regressed"]:
        print("\n⚠ CRITICAL REGRESSION DETECTED", file=sys.stderr)
    else:
        print("\n✓ No critical regression")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Shadou eval comparison")
    parser.add_argument("--baseline", required=True, help="Path to baseline JSON results")
    parser.add_argument("--candidate", required=True, help="Path to candidate JSON results")
    parser.add_argument("--output", default=None, help="Write diff JSON to file")
    args = parser.parse_args(argv)

    try:
        baseline = _load(Path(args.baseline))
        candidate = _load(Path(args.candidate))
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    diff = compare(baseline, candidate)
    _print_report(diff)

    if args.output:
        Path(args.output).write_text(json.dumps(diff, indent=2), encoding="utf-8")

    return 1 if diff["critical_regressed"] else 0


if __name__ == "__main__":
    sys.exit(main())
