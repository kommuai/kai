"""Compute training metrics from eval_run results + item metadata."""

from __future__ import annotations

import re
from typing import Any


def _safe_rate(num: int, den: int) -> float:
    return round(num / den, 4) if den else 1.0


def _items_with_tag(items: list[dict[str, Any]], tag: str) -> list[dict[str, Any]]:
    return [ir for ir in items if tag in (ir.get("tags") or [])]


def _tag_accuracy(items: list[dict[str, Any]], tag: str) -> float | None:
    tagged = _items_with_tag(items, tag)
    if not tagged:
        return None
    ok = sum(1 for ir in tagged if ir.get("passed"))
    return _safe_rate(ok, len(tagged))


def compute_metrics(
    eval_results: dict[str, Any],
    *,
    eval_items: list[dict[str, Any]],
) -> dict[str, float | None]:
    """Derive training gate metrics from eval output."""
    items: list[dict[str, Any]] = list(eval_results.get("items") or [])
    per_tag: dict[str, Any] = eval_results.get("per_tag") or {}

    metrics: dict[str, float | None] = {}

    # Tag accuracies (gate keys accuracy_<tag>)
    for tag, data in per_tag.items():
        if isinstance(data, dict) and data.get("accuracy") is not None:
            metrics[f"accuracy_{tag}"] = float(data["accuracy"])

    # Escalation correctness on must_escalate
    esc_items = _items_with_tag(items, "must_escalate")
    if esc_items:
        ok = sum(1 for ir in esc_items if ir.get("actual_decision") == "escalate_human")
        metrics["escalation_correct_rate"] = _safe_rate(ok, len(esc_items))

    # Abstention utility from harness (must_abstain subset)
    abstain_items = _items_with_tag(items, "must_abstain")
    if abstain_items:
        ok = sum(1 for ir in abstain_items if ir.get("actual_decision") == "abstain")
        metrics["abstention_utility"] = _safe_rate(ok, len(abstain_items))

    metrics["citation_support_rate"] = eval_results.get("citation_support_rate")
    vfr = eval_results.get("verification_flag_rate")
    if vfr is not None:
        metrics["verification_flag_rate"] = float(vfr)

    # Workflow steps: keyword presence in answer for items with expected_steps
    step_total = 0
    step_ok = 0
    for ir, spec in zip(items, eval_items):
        steps = spec.get("expected_steps") or []
        if not steps:
            continue
        answer = (ir.get("answer") or "").lower()
        step_total += len(steps)
        for step in steps:
            token = str(step).lower().replace("_", " ")
            if token in answer or any(w in answer for w in token.split() if len(w) > 3):
                step_ok += 1
    if step_total:
        metrics["workflow_step_score"] = _safe_rate(step_ok, step_total)

    # No guess: ungrounded direct_answer on must_abstain / no_guess tags
    guess_items = _items_with_tag(items, "must_abstain") + _items_with_tag(items, "no_guess")
    if guess_items:
        bad = sum(
            1
            for ir in guess_items
            if ir.get("actual_decision") == "direct_answer" and not ir.get("grounded")
        )
        metrics["no_guess_rate"] = _safe_rate(len(guess_items) - bad, len(guess_items))

    # Ticket type (items with expected_ticket_type in spec — match via tags)
    tt_items = [ir for ir in items if "ticket_type" in " ".join(ir.get("tags") or [])]
    if tt_items:
        ok = sum(1 for ir in tt_items if ir.get("passed"))
        metrics["ticket_type_accuracy"] = _safe_rate(ok, len(tt_items))

    # Handoff summary when escalating
    handoff_ok = 0
    handoff_total = 0
    for ir, spec in zip(items, eval_items):
        fields = spec.get("expected_handoff_fields") or []
        if not fields:
            continue
        if ir.get("actual_decision") != "escalate_human":
            continue
        handoff_total += 1
        answer = (ir.get("answer") or "").lower()
        hits = sum(1 for f in fields if str(f).lower().replace("_", " ") in answer)
        if hits >= max(1, len(fields) // 2):
            handoff_ok += 1
    if handoff_total:
        metrics["handoff_summary_score"] = _safe_rate(handoff_ok, handoff_total)
        metrics["escalation_summary_complete"] = metrics["handoff_summary_score"]

    # Paraphrase consistency by variant_group
    groups: dict[str, list[str]] = {}
    for ir, spec in zip(items, eval_items):
        vg = spec.get("variant_group")
        if vg:
            groups.setdefault(str(vg), []).append(str(ir.get("actual_decision") or ""))
    if groups:
        consistent = sum(1 for decisions in groups.values() if len(set(decisions)) <= 1)
        metrics["paraphrase_consistency"] = _safe_rate(consistent, len(groups))

    # Resolution rate on resolvable tag
    res_items = _items_with_tag(items, "resolvable")
    if res_items:
        ok = sum(
            1
            for ir in res_items
            if ir.get("actual_decision") in ("direct_answer", "clarifying_question")
            or (ir.get("actual_decision") == "escalate_human" and ir.get("passed"))
        )
        metrics["resolution_rate"] = _safe_rate(ok, len(res_items))

    # Tool usage (expected_tools in spec — check evidence tool names)
    tool_ok = 0
    tool_total = 0
    for ir, spec in zip(items, eval_items):
        expected_tools = spec.get("expected_tools") or []
        if not expected_tools:
            continue
        tool_total += 1
        obs = ir.get("tool_names") or []
        if any(t in obs for t in expected_tools):
            tool_ok += 1
    if tool_total:
        metrics["tool_usage_correct"] = _safe_rate(tool_ok, tool_total)

    # Sage composite: average of available core metrics
    parts = [
        metrics.get("resolution_rate"),
        metrics.get("tool_usage_correct"),
        metrics.get("escalation_correct_rate"),
        _tag_accuracy(items, "sage_routing"),
    ]
    vals = [float(p) for p in parts if p is not None]
    if vals:
        metrics["sage_score"] = round(sum(vals) / len(vals), 4)

    return metrics


def check_gates(
    gates: dict[str, float],
    metrics: dict[str, float | None],
) -> list[dict[str, Any]]:
    """Return gate rows with ok flag."""
    rows: list[dict[str, Any]] = []
    for name, threshold in gates.items():
        if name.endswith("_max"):
            metric_name = name[: -len("_max")]
            value = metrics.get(metric_name)
            if value is None:
                rows.append({"name": name, "value": None, "threshold": threshold, "ok": True})
                continue
            ok = float(value) <= threshold
        else:
            value = metrics.get(name)
            if value is None:
                # Try accuracy_<tag> alias
                if name.startswith("accuracy_"):
                    value = metrics.get(name)
            if value is None:
                rows.append({"name": name, "value": None, "threshold": threshold, "ok": False})
                continue
            ok = float(value) >= threshold
        rows.append(
            {
                "name": name,
                "value": value,
                "threshold": threshold,
                "ok": ok,
            }
        )
    return rows
