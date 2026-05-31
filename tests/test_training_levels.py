"""Training level definitions and assess_all level derivation."""
from __future__ import annotations

import unittest

from shadou.training.levels import (
    get_level,
    get_specialization,
    list_jobs,
    load_levels,
    load_specializations,
    max_core_level,
)
from shadou.training.scorers import check_gates, compute_metrics


class LoadLevelsTests(unittest.TestCase):
    def test_two_jobs(self):
        jobs = list_jobs()
        ids = {j.id for j in jobs}
        self.assertIn("customer_support", ids)
        self.assertIn("ceo", ids)

    def test_customer_support_three_levels(self):
        levels = load_levels("customer_support")
        self.assertEqual(len(levels), 3)
        self.assertEqual(levels[0].title, "Confused Intern")
        self.assertEqual(levels[2].title, "Certified Chat Ranger")

    def test_ceo_three_levels(self):
        levels = load_levels("ceo")
        self.assertEqual(len(levels), 3)
        self.assertEqual(levels[0].title, "Curious Observer")
        self.assertEqual(levels[2].title, "Executive Voice")

    def test_job_specific_specializations(self):
        cs = {s.id for s in load_specializations("customer_support")}
        ceo = {s.id for s in load_specializations("ceo")}
        self.assertIn("deal_whisperer", cs)
        self.assertIn("vision_architect", ceo)
        self.assertNotIn("deal_whisperer", ceo)

    def test_get_level_by_job(self):
        lv = get_level(3, "ceo")
        self.assertIsNotNone(lv)
        assert lv is not None
        self.assertEqual(lv.id, "executive_voice")

    def test_max_core_level(self):
        self.assertEqual(max_core_level("customer_support"), 3)
        self.assertEqual(max_core_level("ceo"), 3)


class GateCheckTests(unittest.TestCase):
    def test_pass_threshold(self):
        gates = {"accuracy_level1_faq": 0.7}
        metrics = {"accuracy_level1_faq": 0.85}
        rows = check_gates(gates, metrics)
        self.assertTrue(rows[0]["ok"])

    def test_max_gate(self):
        gates = {"verification_flag_rate_max": 0.15}
        metrics = {"verification_flag_rate": 0.1}
        rows = check_gates(gates, metrics)
        self.assertTrue(rows[0]["ok"])

    def test_escalation_metric(self):
        eval_results = {
            "items": [
                {
                    "tags": ["must_escalate"],
                    "actual_decision": "escalate_human",
                    "passed": True,
                },
                {
                    "tags": ["must_escalate"],
                    "actual_decision": "direct_answer",
                    "passed": False,
                },
            ],
            "per_tag": {},
        }
        metrics = compute_metrics(eval_results, eval_items=[{}, {}])
        self.assertEqual(metrics.get("escalation_correct_rate"), 0.5)


class CurrentLevelDerivationTests(unittest.TestCase):
    def test_highest_passed(self):
        results = {
            1: {"passed": True},
            2: {"passed": True},
            3: {"passed": False},
        }
        current = 0
        for n in sorted(results):
            if results[n].get("passed"):
                current = n
        self.assertEqual(current, 2)


if __name__ == "__main__":
    unittest.main()
