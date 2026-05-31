"""Phase 2-D: Expanded eval metrics — verification_flag_rate + gates."""
from __future__ import annotations

import unittest

from shadou.tools.eval_run import _check_gates, run_eval


class VerificationFlagRateTests(unittest.TestCase):
    """Verify verification_flag_rate is present in run_eval output."""

    def test_verification_flag_rate_in_results(self):
        items = [{"question": "hi", "expected_decision": "direct_answer", "tags": []}]
        results = run_eval(items, open_book=True)
        self.assertIn("verification_flag_rate", results)

    def test_verification_flag_rate_is_float(self):
        items = [{"question": "hello", "expected_decision": "direct_answer", "tags": []}]
        results = run_eval(items, open_book=True)
        rate = results["verification_flag_rate"]
        self.assertIsInstance(rate, float)
        self.assertGreaterEqual(rate, 0.0)
        self.assertLessEqual(rate, 1.0)

    def test_item_results_have_verification_flagged_field(self):
        items = [{"question": "test question", "expected_decision": "direct_answer", "tags": []}]
        results = run_eval(items, open_book=True)
        for ir in results["items"]:
            self.assertIn("verification_flagged", ir)
            self.assertIsInstance(ir["verification_flagged"], bool)

    def test_empty_items_has_zero_flag_rate(self):
        results = run_eval([])
        # Empty run returns None accuracy, verification_flag_rate should be absent or 0
        self.assertNotIn("verification_flag_rate", results)


class ExpandedGatesTests(unittest.TestCase):
    """Gates now include citation_support_rate threshold."""

    def _results(self, accuracy=1.0, csr=1.0, vfr=0.0, tag_accuracy=None):
        per_tag = {}
        if tag_accuracy is not None:
            per_tag["critical"] = {"accuracy": tag_accuracy, "total": 10, "correct": int(tag_accuracy * 10)}
        return {
            "accuracy": accuracy,
            "citation_support_rate": csr,
            "verification_flag_rate": vfr,
            "per_tag": per_tag,
        }

    def test_citation_support_rate_gate_pass(self):
        failures = _check_gates(self._results(csr=0.95), {"citation_support_rate": 0.90})
        self.assertEqual(failures, [])

    def test_citation_support_rate_gate_fail(self):
        failures = _check_gates(self._results(csr=0.80), {"citation_support_rate": 0.90})
        self.assertEqual(len(failures), 1)
        self.assertIn("citation_support_rate", failures[0])

    def test_verification_flag_rate_gate(self):
        # If flag rate is too HIGH, gate fails (tenant sets max, not min)
        # The gate is a lower-bound check, so verification_flag_rate gate
        # passes when actual >= threshold. For a "max flag rate" scenario
        # tenants should set an inverted metric. We test standard gate behaviour.
        failures = _check_gates(self._results(vfr=0.05), {"verification_flag_rate": 0.10})
        # 0.05 < 0.10 → failure (flag rate is below the gate threshold — unusual use case)
        self.assertEqual(len(failures), 1)

    def test_multiple_gates_all_fail(self):
        failures = _check_gates(
            self._results(accuracy=0.80, csr=0.70),
            {"accuracy": 0.90, "citation_support_rate": 0.85},
        )
        self.assertEqual(len(failures), 2)

    def test_per_tag_critical_gate_with_expanded_results(self):
        failures = _check_gates(self._results(tag_accuracy=0.94), {"accuracy_critical": 0.97})
        self.assertEqual(len(failures), 1)
        self.assertIn("accuracy_critical", failures[0])

    def test_none_metric_skipped(self):
        # citation_support_rate may be None when no direct answers
        results = {"accuracy": 0.9, "citation_support_rate": None, "per_tag": {}}
        failures = _check_gates(results, {"citation_support_rate": 0.90})
        self.assertEqual(failures, [])


class LiveRunExpandedMetricsTests(unittest.TestCase):
    """Integration: live run_eval includes all expanded metric keys."""

    def test_all_metric_keys_present(self):
        items = [
            {"question": "hi", "expected_decision": "direct_answer", "tags": ["critical"]},
            {"question": "what is the price", "expected_decision": "direct_answer", "tags": []},
        ]
        results = run_eval(items, open_book=True)
        for key in ("total", "accuracy", "citation_support_rate", "abstention_utility",
                    "verification_flag_rate", "per_tag"):
            self.assertIn(key, results, f"Missing metric key: {key}")

    def test_per_tag_critical_in_results(self):
        items = [{"question": "hello", "expected_decision": "direct_answer", "tags": ["critical"]}]
        results = run_eval(items, open_book=True)
        self.assertIn("critical", results["per_tag"])


if __name__ == "__main__":
    unittest.main()
