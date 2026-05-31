"""Phase 3-A: Contradiction register — detect_conflicts + verifier integration."""
from __future__ import annotations

import unittest

from shadou.support_runtime.models import EvidenceItem, RuntimeResult
from shadou.support_runtime.verifier import detect_conflicts, verify_result


def _ev(source_id: str, snippet: str = "", score: float = 0.8, status: str = "supported") -> EvidenceItem:
    return EvidenceItem(tool="search_faq", source_id=source_id, snippet=snippet, score=score, support_status=status)


class DetectConflictsTests(unittest.TestCase):
    def test_no_snippets_no_conflicts(self):
        items = [_ev("faq:price"), _ev("faq:price")]
        conflicts = detect_conflicts(items)
        self.assertEqual(conflicts, [])

    def test_same_intent_same_text_no_conflict(self):
        text = "The price is RM200 per unit valid warranty"
        items = [_ev("faq:price", text), _ev("faq:price", text)]
        conflicts = detect_conflicts(items)
        self.assertEqual(conflicts, [])

    def test_same_intent_different_text_conflict(self):
        a = _ev("faq:price", "The price is RM200 per unit")
        b = _ev("faq:price", "Totally unrelated content about animals zebra giraffe lion")
        conflicts = detect_conflicts([a, b])
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0]["source_id_a"], "faq:price")
        self.assertEqual(conflicts[0]["reason"], "low_overlap")
        self.assertIn("overlap", conflicts[0])

    def test_different_intent_root_no_conflict(self):
        a = _ev("faq:price", "RM200 unit pricing")
        b = _ev("faq:warranty", "completely different zebra giraffe animals")
        conflicts = detect_conflicts([a, b])
        self.assertEqual(conflicts, [])

    def test_single_item_no_conflict(self):
        self.assertEqual(detect_conflicts([_ev("faq:x", "some text")]), [])

    def test_conflict_has_overlap_field(self):
        a = _ev("faq:q", "The price is two hundred ringgit malaysia")
        b = _ev("faq:q", "Completely unrelated animals zebra giraffe tiger")
        conflicts = detect_conflicts([a, b])
        if conflicts:
            self.assertIsInstance(conflicts[0]["overlap"], float)
            self.assertGreaterEqual(conflicts[0]["overlap"], 0.0)
            self.assertLessEqual(conflicts[0]["overlap"], 1.0)


class VerifierConflictIntegrationTests(unittest.TestCase):
    def _make_result(self, evidence: list[EvidenceItem]) -> RuntimeResult:
        return RuntimeResult(
            decision="direct_answer", answer="Answer", confidence=0.85, evidence_ledger=evidence
        )

    def test_conflicting_snippets_flagged_in_metadata(self):
        a = _ev("faq:policy", "Warranty is twelve months from purchase date")
        b = _ev("faq:policy", "Completely unrelated animals zebra giraffe tiger elephant")
        result = verify_result(self._make_result([a, b]))
        v = result.metadata.get("verification", {})
        self.assertTrue(v.get("flagged"))
        self.assertIn("conflict", v.get("reason", ""))

    def test_conflicts_in_top_level_metadata(self):
        a = _ev("faq:pricing", "RM200 per unit")
        b = _ev("faq:pricing", "animals zebra giraffe totally different things lion")
        result = verify_result(self._make_result([a, b]))
        top_conflicts = result.metadata.get("conflicts") or []
        self.assertIsInstance(top_conflicts, list)

    def test_no_conflicts_when_consistent(self):
        a = _ev("faq:price", "Price is RM200 per unit for customers")
        b = _ev("faq:price", "Customers pay RM200 per unit pricing")
        result = verify_result(self._make_result([a, b]))
        conflicts = result.metadata.get("conflicts") or []
        self.assertEqual(conflicts, [])

    def test_abstain_on_fail_with_contradiction(self):
        import shadou.support_runtime.verifier as vm
        original = vm._eval_block
        vm._eval_block = lambda: {"verifier_on_fail": "abstain", "contradiction_token_overlap": 0.3}
        try:
            a = _ev("faq:x", "RM200 price warranty unit")
            b = _ev("faq:x", "completely unrelated animals zebra giraffe")
            result = verify_result(self._make_result([a, b]))
            if result.metadata.get("verification", {}).get("flagged"):
                self.assertEqual(result.decision, "abstain")
        finally:
            vm._eval_block = original

    def test_conflicts_populated_with_both_source_ids(self):
        a = _ev("faq:q", "RM200 per unit warranty included")
        b = _ev("faq:q", "Completely unrelated things animals zebra giraffe")
        result = verify_result(self._make_result([a, b]))
        verification_conflicts = result.metadata.get("verification", {}).get("conflicts") or []
        for c in verification_conflicts:
            self.assertIn("source_id_a", c)
            self.assertIn("source_id_b", c)


if __name__ == "__main__":
    unittest.main()
