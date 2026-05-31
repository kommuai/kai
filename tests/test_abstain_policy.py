"""Phase 1-B: Abstain decision type + grounding policy gate."""
from __future__ import annotations

import unittest

from kai.support_runtime.models import DecisionType, EvidenceItem, RuntimeResult


class AbstainDecisionTypeTests(unittest.TestCase):
    def test_abstain_is_valid_decision_type(self):
        # Should not raise — "abstain" must be in the Literal
        rr = RuntimeResult(decision="abstain", answer="I cannot answer that.", confidence=0.3)
        self.assertEqual(rr.decision, "abstain")

    def test_direct_answer_still_valid(self):
        rr = RuntimeResult(decision="direct_answer", answer="ok", confidence=0.9)
        self.assertEqual(rr.decision, "direct_answer")


class MaybeForceAbstainTests(unittest.TestCase):
    """Unit tests for gateway._maybe_force_abstain without running full service."""

    def _make_result(self, decision="direct_answer", confidence=0.3, source_ids=None, observations=None):
        meta = {"evidence": {"observations": observations or []}}
        return RuntimeResult(
            decision=decision,
            answer="Some answer",
            confidence=confidence,
            source_ids=source_ids or [],
            metadata=meta,
        )

    def _call(self, result, text="test", lang="EN"):
        from kai.support_runtime.gateway import _maybe_force_abstain
        return _maybe_force_abstain(result, text, lang)

    def test_low_confidence_no_evidence_forces_abstain(self):
        result = self._make_result(confidence=0.2, source_ids=[], observations=[])
        out = self._call(result)
        self.assertEqual(out.decision, "abstain")

    def test_high_confidence_no_evidence_not_abstained(self):
        result = self._make_result(confidence=0.95, source_ids=[], observations=[])
        out = self._call(result)
        self.assertNotEqual(out.decision, "abstain")

    def test_low_confidence_with_faq_source_id_not_abstained(self):
        result = self._make_result(confidence=0.2, source_ids=["faq:product_warranty"])
        out = self._call(result)
        self.assertNotEqual(out.decision, "abstain")

    def test_low_confidence_with_grounded_observation_not_abstained(self):
        obs = [{
            "tool": "search_faq",
            "result": {
                "ok": True,
                "results": [{
                    "source_id": "faq:pricing",
                    "score": 0.9,
                    "text": "Q: price\nA: RM200",
                    "metadata": {"intent_id": "pricing"},
                }],
            },
        }]
        result = self._make_result(confidence=0.2, observations=obs)
        out = self._call(result)
        self.assertNotEqual(out.decision, "abstain")

    def test_already_escalate_not_changed(self):
        result = self._make_result(decision="escalate_human", confidence=0.1)
        out = self._call(result)
        self.assertEqual(out.decision, "escalate_human")

    def test_abstain_answer_is_non_empty(self):
        result = self._make_result(confidence=0.1, source_ids=[], observations=[])
        out = self._call(result)
        self.assertTrue(len(out.answer.strip()) > 0)

    def test_abstain_copy_language_bm(self):
        result = self._make_result(confidence=0.1)
        en_out = self._call(result, lang="EN")
        bm_out = self._call(result, lang="BM")
        self.assertNotEqual(en_out.answer, bm_out.answer)

    def test_abstain_threshold_from_runtime_settings(self):
        from kai.workspace.runtime_settings import get_runtime_settings
        rs = get_runtime_settings()
        # Default threshold must be between 0 and 1
        self.assertGreater(rs.eval_abstain_threshold, 0.0)
        self.assertLess(rs.eval_abstain_threshold, 1.0)


if __name__ == "__main__":
    unittest.main()
