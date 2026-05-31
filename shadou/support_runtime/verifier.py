"""Rules-based verifier for Shadou agent answers.

After the ReAct loop produces a direct_answer, the verifier checks whether
the evidence ledger actually supports it.  By default it runs rules-only
(no extra LLM call).  Tenants opt into LLM mode via workspace.yaml.

workspace.yaml knobs (all under ``eval:``):
    verifier_mode: rules      # rules | llm (default: rules)
    verifier_on_fail: flag    # flag | abstain (default: flag)
    verifier_min_score: 0.0   # minimum evidence score to count as supported (default: 0)
    contradiction_token_overlap: 0.3  # max shared token fraction before two items are "different" enough to flag
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, replace
from typing import Any

from shadou.support_runtime.models import EvidenceItem, RuntimeResult

import re as _re
from datetime import date as _date, datetime as _datetime

log = logging.getLogger("shadou.verifier")


# --------------------------------------------------------------------------- #
# Config helpers
# --------------------------------------------------------------------------- #

def _eval_block() -> dict[str, Any]:
    try:
        from shadou.workspace.runtime_settings import load_workspace_settings_yaml
        data = load_workspace_settings_yaml()
        block = data.get("eval")
        return block if isinstance(block, dict) else {}
    except Exception:  # noqa: BLE001
        return {}


def _verifier_mode() -> str:
    return str(_eval_block().get("verifier_mode") or "rules").strip().lower()


def _verifier_on_fail() -> str:
    return str(_eval_block().get("verifier_on_fail") or "flag").strip().lower()


def _verifier_min_score() -> float:
    raw = _eval_block().get("verifier_min_score")
    try:
        return float(raw) if raw is not None else 0.0
    except (TypeError, ValueError):
        return 0.0


def _max_corpus_age_days() -> int:
    raw = _eval_block().get("max_corpus_age_days")
    try:
        return int(raw) if raw is not None else 30
    except (TypeError, ValueError):
        return 30


def _contradiction_overlap_threshold() -> float:
    """Max token-overlap ratio before two snippets are considered contradictory."""
    raw = _eval_block().get("contradiction_token_overlap")
    try:
        return float(raw) if raw is not None else 0.3
    except (TypeError, ValueError):
        return 0.3


# --------------------------------------------------------------------------- #
# Corpus staleness
# --------------------------------------------------------------------------- #

def check_corpus_staleness() -> bool:
    """Return True if corpus_map.json is older than eval.max_corpus_age_days.

    Returns False (not stale) if the file is missing or compiled_at is absent.
    """
    try:
        from shadou.settings import get_settings
        from shadou.workspace.manifest import load_workspace_manifest

        compiled_dir = get_settings().shadou_home / load_workspace_manifest().paths.knowledge_compiled_dir
        map_path = compiled_dir / "corpus_map.json"
        if not map_path.is_file():
            return False
        data = json.loads(map_path.read_text(encoding="utf-8"))
        compiled_at_str = str(data.get("compiled_at") or "").strip()
        if not compiled_at_str:
            return False
        compiled_at = _datetime.strptime(compiled_at_str[:10], "%Y-%m-%d").date()
        age_days = (_date.today() - compiled_at).days
        return age_days > _max_corpus_age_days()
    except Exception:  # noqa: BLE001
        return False


# --------------------------------------------------------------------------- #
# Core verification logic (rules)
# --------------------------------------------------------------------------- #

@dataclass
class VerifierOutcome:
    passed: bool
    reason: str
    flagged: bool = False
    conflicts: list[dict[str, Any]] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.conflicts is None:
            self.conflicts = []


def _token_set(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]{3,}", (text or "").lower())}


def _overlap_ratio(a: str, b: str) -> float:
    """Jaccard-style overlap between two token sets."""
    ta, tb = _token_set(a), _token_set(b)
    if not ta or not tb:
        return 1.0  # treat empty vs empty as identical (no conflict)
    intersection = len(ta & tb)
    union = len(ta | tb)
    return intersection / union if union else 1.0


def detect_conflicts(evidence_ledger: list[EvidenceItem]) -> list[dict[str, Any]]:
    """Identify pairs of evidence items that share an intent but have divergent text.

    Two items conflict when they:
      - come from the same source_id prefix (same intent) OR have non-empty snippets
      - but their snippet token overlap is below the contradiction threshold

    Returns a list of conflict records:
        {"source_id_a": ..., "source_id_b": ..., "overlap": float, "reason": "low_overlap"}
    """
    threshold = _contradiction_overlap_threshold()
    conflicts: list[dict[str, Any]] = []

    items_with_snippets = [e for e in evidence_ledger if e.snippet]
    for i, a in enumerate(items_with_snippets):
        for b in items_with_snippets[i + 1 :]:
            # Only flag items that share the exact same source_id (same intent/chunk)
            if a.source_id != b.source_id:
                continue
            overlap = _overlap_ratio(a.snippet, b.snippet)
            if overlap < threshold:
                conflicts.append({
                    "source_id_a": a.source_id,
                    "source_id_b": b.source_id,
                    "overlap": round(overlap, 4),
                    "reason": "low_overlap",
                })
    return conflicts


def _rules_verify(evidence_ledger: list[EvidenceItem], min_score: float) -> VerifierOutcome:
    """Pure rule check — no LLM call."""
    if not evidence_ledger:
        return VerifierOutcome(passed=False, reason="no_evidence", flagged=True)

    strong = [e for e in evidence_ledger if e.support_status != "conflicting" and e.score >= min_score]
    if not strong:
        return VerifierOutcome(
            passed=False,
            reason=f"no_evidence_above_min_score_{min_score}",
            flagged=True,
        )

    # Check items already tagged conflicting by agent loop
    pre_flagged: list[dict[str, Any]] = [
        {"source_id": e.source_id, "tool": e.tool}
        for e in evidence_ledger
        if e.support_status == "conflicting"
    ]

    # Check snippet-based contradictions between items from the same intent
    detected = detect_conflicts(evidence_ledger)
    all_conflicts = pre_flagged + detected

    if all_conflicts:
        return VerifierOutcome(
            passed=False,
            reason="conflicting_evidence",
            flagged=True,
            conflicts=all_conflicts,
        )

    return VerifierOutcome(passed=True, reason="rules_ok")


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #

def verify_result(result: RuntimeResult) -> RuntimeResult:
    """Run the verifier on a RuntimeResult; return an updated copy.

    Only acts on ``direct_answer`` decisions.  Other decisions pass through
    unchanged.

    The outcome is written to ``result.metadata["verification"]`` as:
        {
            "passed": bool,
            "reason": str,
            "flagged": bool,
            "conflicts": [...],
            "mode": "rules"|"llm",
        }
    """
    if result.decision != "direct_answer":
        return result

    mode = _verifier_mode()
    on_fail = _verifier_on_fail()
    min_score = _verifier_min_score()
    stale = check_corpus_staleness()

    outcome = _rules_verify(result.evidence_ledger, min_score)
    log.debug(
        "verifier[%s] passed=%s reason=%s flagged=%s",
        mode, outcome.passed, outcome.reason, outcome.flagged,
    )

    verification_meta: dict[str, Any] = {
        "passed": outcome.passed,
        "reason": outcome.reason,
        "flagged": outcome.flagged,
        "conflicts": outcome.conflicts,
        "mode": mode,
    }

    # Also surface conflicts at the top level of metadata for easy access
    new_conflicts = outcome.conflicts or []

    existing_conflicts = list((result.metadata or {}).get("conflicts") or [])
    new_meta = {
        **(result.metadata or {}),
        "verification": verification_meta,
        "conflicts": existing_conflicts + new_conflicts,
        "stale_evidence": stale,
    }

    if outcome.passed:
        return replace(result, metadata=new_meta)

    # Verification failed — apply on_fail policy
    if on_fail == "abstain":
        try:
            from shadou.workspace.runtime_settings import get_runtime_settings
            rs = get_runtime_settings()
            abstain_copy = rs.eval_abstain_copy_en
        except Exception:  # noqa: BLE001
            abstain_copy = (
                "I don't have enough information to answer that reliably. "
                "Type LA for a live agent."
            )
        return replace(
            result,
            decision="abstain",
            answer=abstain_copy,
            fallback_reason=f"verifier_failed:{outcome.reason}",
            metadata=new_meta,
        )

    # Default: flag only — keep answer, mark metadata
    return replace(result, metadata=new_meta)
