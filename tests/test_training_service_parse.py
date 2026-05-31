"""training_service stdout JSON parsing."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[1] / "studio" / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))


class ParseStdoutTests(unittest.TestCase):
    def test_pretty_json(self):
        from training_service import _parse_assessment_stdout

        payload = {"current_level": 2, "level_results": {"1": {"passed": True}}}
        text = json.dumps(payload, indent=2)
        out = _parse_assessment_stdout(text)
        self.assertEqual(out["current_level"], 2)

    def test_compact_json(self):
        from training_service import _parse_assessment_stdout

        text = '{"current_level": 1, "passed": true}'
        out = _parse_assessment_stdout(text)
        self.assertEqual(out["current_level"], 1)


if __name__ == "__main__":
    unittest.main()
