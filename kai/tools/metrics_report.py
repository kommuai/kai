"""Rolling production metrics report for Kai.

Reads the turn_metrics.jsonl file and prints a summary over a configurable
time window (default: last 24 hours).

Usage:
    python -m kai.tools.metrics_report [--hours 24] [--file PATH]
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


def _load_rows(path: Path, since: datetime) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        ts_str = row.get("ts") or ""
        try:
            ts = datetime.fromisoformat(ts_str)
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        if ts >= since:
            rows.append(row)
    return rows


def _safe_rate(num: int, den: int) -> float:
    return round(num / den, 4) if den else 0.0


def compute_report(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(rows)
    if total == 0:
        return {"total": 0, "unverified_rate": None, "abstain_rate": None, "avg_tool_steps": None,
                "stale_citation_rate": None, "verification_flag_rate": None}

    flagged = sum(1 for r in rows if r.get("verification_flagged"))
    abstained = sum(1 for r in rows if r.get("abstained"))
    stale = sum(1 for r in rows if r.get("stale_evidence"))
    tool_counts = [int(r.get("tool_count") or 0) for r in rows]

    return {
        "total": total,
        "unverified_rate": _safe_rate(flagged, total),
        "abstain_rate": _safe_rate(abstained, total),
        "avg_tool_steps": round(sum(tool_counts) / total, 2),
        "stale_citation_rate": _safe_rate(stale, total),
        "verification_flag_rate": _safe_rate(flagged, total),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Kai production metrics report")
    parser.add_argument("--hours", type=int, default=24, help="Rolling window in hours (default 24)")
    parser.add_argument("--file", default=None, help="Path to turn_metrics.jsonl")
    args = parser.parse_args(argv)

    if args.file:
        path = Path(args.file)
    else:
        try:
            from kai.support_runtime.metrics import _metrics_path
            path = _metrics_path()
        except Exception:  # noqa: BLE001
            path = Path("data/turn_metrics.jsonl")

    since = datetime.now(timezone.utc) - timedelta(hours=args.hours)
    rows = _load_rows(path, since)
    report = compute_report(rows)

    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
