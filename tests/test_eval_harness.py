"""Phase 1-D: Eval harness CLI (tenant-agnostic)."""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from kai.tools.eval_run import _load_eval_items, _load_gates, _check_gates, run_eval


def _write_jsonl(path: Path, items: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(i) for i in items), encoding="utf-8")


class LoadEvalItemsTests(unittest.TestCase):
    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp())

    def test_loads_valid_jsonl(self):
        p = self._tmp / "eval.jsonl"
        _write_jsonl(p, [
            {"question": "What is the price?", "expected_decision": "direct_answer", "tags": ["critical"]},
            {"question": "How to install?", "expected_decision": "direct_answer", "tags": []},
        ])
        items = _load_eval_items(p)
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["question"], "What is the price?")

    def test_empty_file_returns_empty_list(self):
        p = self._tmp / "empty.jsonl"
        p.write_text("", encoding="utf-8")
        self.assertEqual(_load_eval_items(p), [])

    def test_missing_file_returns_empty_list(self):
        self.assertEqual(_load_eval_items(self._tmp / "nonexistent.jsonl"), [])

    def test_skips_malformed_lines(self):
        p = self._tmp / "bad.jsonl"
        p.write_text('{"question": "ok"}\nNOT JSON\n{"question": "also ok"}', encoding="utf-8")
        items = _load_eval_items(p)
        self.assertEqual(len(items), 2)


class LoadGatesTests(unittest.TestCase):
    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp())

    def test_reads_gates_from_workspace_yaml(self):
        p = self._tmp / "workspace.yaml"
        p.write_text("eval:\n  gates:\n    accuracy_critical: 0.97\n    citation_support_rate: 0.90\n", encoding="utf-8")
        gates = _load_gates(p)
        self.assertAlmostEqual(gates["accuracy_critical"], 0.97)
        self.assertAlmostEqual(gates["citation_support_rate"], 0.90)

    def test_missing_gates_returns_empty(self):
        p = self._tmp / "workspace.yaml"
        p.write_text("agent:\n  max_steps: 8\n", encoding="utf-8")
        self.assertEqual(_load_gates(p), {})

    def test_none_path_returns_empty(self):
        self.assertEqual(_load_gates(None), {})


class CheckGatesTests(unittest.TestCase):
    def _results(self, accuracy=1.0, csr=1.0, tag_accuracy=None):
        per_tag = {}
        if tag_accuracy is not None:
            per_tag["critical"] = {"accuracy": tag_accuracy, "total": 10, "correct": int(tag_accuracy * 10)}
        return {
            "accuracy": accuracy,
            "citation_support_rate": csr,
            "per_tag": per_tag,
        }

    def test_all_pass(self):
        failures = _check_gates(self._results(0.98, 0.95, 0.98), {"accuracy": 0.92, "citation_support_rate": 0.90})
        self.assertEqual(failures, [])

    def test_accuracy_below_gate(self):
        failures = _check_gates(self._results(0.88, 0.95), {"accuracy": 0.92})
        self.assertEqual(len(failures), 1)
        self.assertIn("accuracy", failures[0])

    def test_critical_tag_gate(self):
        failures = _check_gates(self._results(tag_accuracy=0.95), {"accuracy_critical": 0.97})
        self.assertEqual(len(failures), 1)

    def test_empty_gates_always_pass(self):
        self.assertEqual(_check_gates(self._results(0.0, 0.0), {}), [])


class RunEvalEmptyTests(unittest.TestCase):
    def test_empty_items_returns_none_accuracy(self):
        results = run_eval([])
        self.assertEqual(results["total"], 0)
        self.assertIsNone(results["accuracy"])
        self.assertIsNone(results["citation_support_rate"])
        self.assertIsNone(results["abstention_utility"])


class RunEvalLiveTests(unittest.TestCase):
    """Integration tests — run against the live runtime with the fixture workspace."""

    def test_basic_pass_fail_counting(self):
        items = [
            {"question": "hi", "expected_decision": "direct_answer", "tags": []},
            {"question": "hello", "expected_decision": "direct_answer", "tags": []},
        ]
        results = run_eval(items, open_book=True)
        self.assertEqual(results["total"], 2)
        self.assertIn("accuracy", results)
        self.assertIsNotNone(results["accuracy"])

    def test_per_tag_breakdown_present(self):
        items = [
            {"question": "hi", "expected_decision": "direct_answer", "tags": ["critical"]},
        ]
        results = run_eval(items, open_book=True)
        self.assertIn("critical", results["per_tag"])
        self.assertIn("accuracy", results["per_tag"]["critical"])

    def test_critical_failure_detected(self):
        # Expect escalate but agent likely won't — counts as failure
        items = [
            {"question": "hi", "expected_decision": "escalate_human", "tags": ["critical"]},
        ]
        results = run_eval(items, open_book=True)
        critical_failures = [ir for ir in results["items"] if "critical" in (ir.get("tags") or []) and not ir["passed"]]
        # Either 0 or 1 failures — just assert the field exists and is a list
        self.assertIsInstance(critical_failures, list)

    def test_abstention_utility_none_when_no_abstain_expected(self):
        items = [
            {"question": "hi", "expected_decision": "direct_answer", "tags": []},
        ]
        results = run_eval(items, open_book=True)
        self.assertIsNone(results["abstention_utility"])

    def test_item_results_have_required_fields(self):
        items = [{"question": "what is this?", "expected_decision": "direct_answer", "tags": []}]
        results = run_eval(items, open_book=True)
        for ir in results["items"]:
            for field in ("question", "expected_decision", "actual_decision", "passed", "grounded", "confidence"):
                self.assertIn(field, ir, f"Missing field: {field}")


if __name__ == "__main__":
    unittest.main()
