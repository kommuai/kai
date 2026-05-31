"""Phase 3-B: eval_compare CLI — baseline vs candidate diff."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from kai.tools.eval_compare import compare


def _results(
    accuracy: float = 1.0,
    csr: float | None = 1.0,
    items: list[dict] | None = None,
    tag_accuracy: float | None = None,
) -> dict:
    per_tag: dict = {}
    if tag_accuracy is not None:
        per_tag["critical"] = {"accuracy": tag_accuracy, "total": 10, "correct": int(tag_accuracy * 10)}
    return {
        "total": len(items or []),
        "accuracy": accuracy,
        "citation_support_rate": csr,
        "per_tag": per_tag,
        "items": items or [],
    }


class CompareTests(unittest.TestCase):
    def test_identical_results_no_regression(self):
        r = _results(accuracy=0.95)
        diff = compare(r, r)
        self.assertFalse(diff["critical_regressed"])
        self.assertEqual(diff["metrics"]["accuracy"]["delta"], 0.0)

    def test_accuracy_improvement_not_regression(self):
        baseline = _results(accuracy=0.90)
        candidate = _results(accuracy=0.95)
        diff = compare(baseline, candidate)
        self.assertFalse(diff["critical_regressed"])
        self.assertGreater(diff["metrics"]["accuracy"]["delta"], 0)

    def test_accuracy_drop_is_regression(self):
        baseline = _results(accuracy=0.95)
        candidate = _results(accuracy=0.88)
        diff = compare(baseline, candidate)
        self.assertTrue(diff["critical_regressed"])
        self.assertTrue(diff["metrics"]["accuracy"]["regressed"])

    def test_critical_tag_regression_detected(self):
        baseline = _results(tag_accuracy=0.97)
        candidate = _results(tag_accuracy=0.91)
        diff = compare(baseline, candidate)
        self.assertTrue(diff["critical_regressed"])
        self.assertTrue(diff["per_tag"]["critical"]["regressed"])

    def test_new_failure_detected(self):
        q = "What is the price?"
        baseline = _results(items=[{"question": q, "passed": True}])
        candidate = _results(items=[{"question": q, "passed": False}])
        diff = compare(baseline, candidate)
        self.assertIn(q, diff["new_failures"])

    def test_fixed_item_detected(self):
        q = "How to install?"
        baseline = _results(items=[{"question": q, "passed": False}])
        candidate = _results(items=[{"question": q, "passed": True}])
        diff = compare(baseline, candidate)
        self.assertIn(q, diff["fixed_items"])

    def test_none_metric_delta_is_none(self):
        baseline = _results(csr=None)
        candidate = _results(csr=None)
        diff = compare(baseline, candidate)
        self.assertIsNone(diff["metrics"]["citation_support_rate"]["delta"])

    def test_summary_counts_correct(self):
        q1, q2 = "Q1?", "Q2?"
        baseline = _results(items=[
            {"question": q1, "passed": True},
            {"question": q2, "passed": False},
        ])
        candidate = _results(items=[
            {"question": q1, "passed": False},
            {"question": q2, "passed": True},
        ])
        diff = compare(baseline, candidate)
        self.assertEqual(diff["summary"]["new_failures_count"], 1)
        self.assertEqual(diff["summary"]["fixed_items_count"], 1)

    def test_no_critical_regression_exit_code_0(self):
        from kai.tools.eval_compare import main
        tmp = Path(tempfile.mkdtemp())
        b = tmp / "baseline.json"
        c = tmp / "candidate.json"
        b.write_text(json.dumps(_results(accuracy=0.95, tag_accuracy=0.97)), encoding="utf-8")
        c.write_text(json.dumps(_results(accuracy=0.97, tag_accuracy=0.98)), encoding="utf-8")
        code = main(["--baseline", str(b), "--candidate", str(c)])
        self.assertEqual(code, 0)

    def test_critical_regression_exit_code_1(self):
        from kai.tools.eval_compare import main
        tmp = Path(tempfile.mkdtemp())
        b = tmp / "baseline.json"
        c = tmp / "candidate.json"
        b.write_text(json.dumps(_results(accuracy=0.97, tag_accuracy=0.97)), encoding="utf-8")
        c.write_text(json.dumps(_results(accuracy=0.85, tag_accuracy=0.85)), encoding="utf-8")
        code = main(["--baseline", str(b), "--candidate", str(c)])
        self.assertEqual(code, 1)

    def test_missing_file_exit_code_2(self):
        from kai.tools.eval_compare import main
        code = main(["--baseline", "/nonexistent/file.json", "--candidate", "/also/missing.json"])
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
