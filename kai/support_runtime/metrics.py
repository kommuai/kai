"""Production turn sampling metrics for Kai.

On every ``run_support_turn`` call, a compact row is appended to a JSONL file.
No user message content is stored — only structural signals.

Row schema:
    {
        "ts": "ISO-8601",
        "tenant_id": "...",
        "decision": "direct_answer|abstain|...",
        "confidence": 0.0-1.0,
        "evidence_count": int,
        "verification_flagged": bool,
        "tool_count": int,
        "abstained": bool,
        "stale_evidence": bool
    }

workspace.yaml knob:
    logging:
        metrics_file: data/turn_metrics.jsonl   # relative to KAI_HOME
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from kai.support_runtime.models import RuntimeResult

log = logging.getLogger("kai.metrics")

_DEFAULT_METRICS_FILE = "data/turn_metrics.jsonl"


def _metrics_path() -> Path:
    try:
        from kai.settings import get_settings
        from kai.workspace.runtime_settings import load_workspace_settings_yaml

        data = load_workspace_settings_yaml()
        logging_block = data.get("logging") if isinstance(data.get("logging"), dict) else {}
        rel = str(logging_block.get("metrics_file") or _DEFAULT_METRICS_FILE).strip()
        return get_settings().kai_home / rel
    except Exception:  # noqa: BLE001
        return Path(_DEFAULT_METRICS_FILE)


def _tenant_id() -> str:
    try:
        from kai.workspace.manifest import load_workspace_manifest
        return load_workspace_manifest().tenant_id or ""
    except Exception:  # noqa: BLE001
        return ""


def record_turn_metrics(result: RuntimeResult) -> None:
    """Append one metrics row to the tenant metrics JSONL file.

    Silently swallows all errors — metrics must never break the main flow.
    """
    try:
        tool_steps = (result.metadata or {}).get("agentic_route", {}).get("steps") or []
        verification = (result.metadata or {}).get("verification") or {}
        row: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "tenant_id": _tenant_id(),
            "decision": result.decision,
            "confidence": round(result.confidence, 4),
            "evidence_count": len(result.evidence_ledger),
            "verification_flagged": bool(verification.get("flagged")),
            "tool_count": len(tool_steps),
            "abstained": result.decision == "abstain",
            "stale_evidence": bool((result.metadata or {}).get("stale_evidence")),
        }
        path = _metrics_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row) + "\n")
    except Exception:  # noqa: BLE001
        log.debug("metrics write failed (non-fatal)", exc_info=True)
