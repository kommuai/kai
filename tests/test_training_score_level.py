"""Training score_level with mocked eval."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from shadou.training.packs import ensure_tenant_training_packs
from shadou.training.score_level import assess_level


class AssessLevelMockedTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self._home = Path(self._tmp)
        (self._home / "workspace.yaml").write_text(
            "version: '2'\ntenant:\n  id: t\n  display_name: T\n  default_lang: en\n",
            encoding="utf-8",
        )
        ensure_tenant_training_packs(self._home)

    @patch("shadou.training.score_level.run_eval")
    def test_level1_pass_mock(self, mock_eval):
        mock_eval.return_value = {
            "total": 4,
            "accuracy": 1.0,
            "citation_support_rate": 1.0,
            "abstention_utility": 1.0,
            "verification_flag_rate": 0.0,
            "per_tag": {
                "level1_faq": {"total": 2, "correct": 2, "accuracy": 1.0},
                "must_escalate": {"total": 1, "correct": 1, "accuracy": 1.0},
                "must_abstain": {"total": 1, "correct": 1, "accuracy": 1.0},
            },
            "items": [
                {
                    "tags": ["level1_faq"],
                    "passed": True,
                    "actual_decision": "direct_answer",
                    "grounded": True,
                    "answer": "We sell support bots.",
                },
                {
                    "tags": ["must_escalate"],
                    "passed": True,
                    "actual_decision": "escalate_human",
                    "answer": "Connecting you to an agent.",
                },
                {
                    "tags": ["must_abstain"],
                    "passed": True,
                    "actual_decision": "abstain",
                    "answer": "I cannot confirm that.",
                },
            ],
        }
        result = assess_level(self._home, 1)
        self.assertTrue(result.passed)
        self.assertGreaterEqual(result.score_pct, 0.8)


if __name__ == "__main__":
    unittest.main()
