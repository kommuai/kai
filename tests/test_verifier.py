"""Phase 2-B: Verifier pass — rules-based, gateway integration."""
from __future__ import annotations

import unittest
from dataclasses import replace

from kai.support_runtime.models import EvidenceItem, RuntimeResult
from kai.support_runtime.verifier import VerifierOutcome, _rules_verify, verify_result


def _make_result(
    decision: str = "direct_answer",
    confidence: float = 0.85,
    evidence: list[EvidenceItem] | None = None,
) -> RuntimeResult:
    return RuntimeResult(
        decision=decision,
        answer="Some answer here.",
        confidence=confidence,
        evidence_ledger=evidence or [],
    )


def _ev(source_id: str = "faq:test", score: float = 0.8, status: str = "supported") -> EvidenceItem:
    return EvidenceItem(tool="search_faq", source_id=source_id, score=score, support_status=status)


class RulesVerifyTests(unittest.TestCase):
    def test_strong_evidence_passes(self):
        outcome = _rules_verify([_ev(score=0.9)], min_score=0.0)
        self.assertTrue(outcome.passed)
        self.assertFalse(outcome.flagged)

    def test_empty_ledger_fails(self):
        outcome = _rules_verify([], min_score=0.0)
        self.assertFalse(outcome.passed)
        self.assertTrue(outcome.flagged)
        self.assertEqual(outcome.reason, "no_evidence")

    def test_conflicting_evidence_fails(self):
        items = [_ev(score=0.9), _ev(source_id="faq:other", score=0.9, status="conflicting")]
        outcome = _rules_verify(items, min_score=0.0)
        self.assertFalse(outcome.passed)
        self.assertTrue(outcome.flagged)
        self.assertEqual(outcome.reason, "conflicting_evidence")
        self.assertEqual(len(outcome.conflicts), 1)

    def test_score_below_min_fails(self):
        outcome = _rules_verify([_ev(score=0.1)], min_score=0.5)
        self.assertFalse(outcome.passed)
        self.assertTrue(outcome.flagged)

    def test_outcome_is_verifier_outcome(self):
        o = _rules_verify([_ev()], min_score=0.0)
        self.assertIsInstance(o, VerifierOutcome)


class VerifyResultTests(unittest.TestCase):
    def test_strong_evidence_passes_no_flag(self):
        result = _make_result(evidence=[_ev(score=0.9)])
        out = verify_result(result)
        v = out.metadata.get("verification", {})
        self.assertTrue(v.get("passed"))
        self.assertFalse(v.get("flagged"))
        self.assertEqual(out.decision, "direct_answer")

    def test_empty_ledger_flags(self):
        result = _make_result(evidence=[])
        out = verify_result(result)
        v = out.metadata.get("verification", {})
        self.assertFalse(v.get("passed"))
        self.assertTrue(v.get("flagged"))
        self.assertEqual(out.decision, "direct_answer")  # default: flag only

    def test_non_direct_answer_passes_through(self):
        result = _make_result(decision="clarifying_question", evidence=[])
        out = verify_result(result)
        self.assertNotIn("verification", out.metadata)

    def test_escalate_passes_through(self):
        result = _make_result(decision="escalate_human", evidence=[])
        out = verify_result(result)
        self.assertNotIn("verification", out.metadata)

    def test_verification_metadata_written(self):
        result = _make_result(evidence=[_ev()])
        out = verify_result(result)
        self.assertIn("verification", out.metadata)
        v = out.metadata["verification"]
        for key in ("passed", "reason", "flagged", "conflicts", "mode"):
            self.assertIn(key, v)

    def test_verifier_mode_in_metadata(self):
        result = _make_result(evidence=[_ev()])
        out = verify_result(result)
        self.assertEqual(out.metadata["verification"]["mode"], "rules")

    def test_conflicting_evidence_recorded(self):
        items = [_ev(), _ev(source_id="faq:b", status="conflicting")]
        result = _make_result(evidence=items)
        out = verify_result(result)
        conflicts = out.metadata["verification"]["conflicts"]
        self.assertEqual(len(conflicts), 1)


class VerifierOnFailAbstainTests(unittest.TestCase):
    """Test the abstain-on-fail policy by patching workspace config."""

    def _patch_eval_block(self, block: dict):
        import kai.support_runtime.verifier as vm
        original = vm._eval_block
        vm._eval_block = lambda: block
        return original

    def test_on_fail_abstain_forces_decision(self):
        import kai.support_runtime.verifier as vm
        original = vm._eval_block
        vm._eval_block = lambda: {"verifier_mode": "rules", "verifier_on_fail": "abstain"}
        try:
            result = _make_result(evidence=[])
            out = verify_result(result)
            self.assertEqual(out.decision, "abstain")
            self.assertIn("verifier_failed", out.fallback_reason)
        finally:
            vm._eval_block = original

    def test_on_fail_flag_keeps_direct_answer(self):
        import kai.support_runtime.verifier as vm
        original = vm._eval_block
        vm._eval_block = lambda: {"verifier_mode": "rules", "verifier_on_fail": "flag"}
        try:
            result = _make_result(evidence=[])
            out = verify_result(result)
            self.assertEqual(out.decision, "direct_answer")
            self.assertTrue(out.metadata["verification"]["flagged"])
        finally:
            vm._eval_block = original


if __name__ == "__main__":
    unittest.main()
