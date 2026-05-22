"""Unit tests for SmartServa visitor row selection (no live HTTP)."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


def _load_create_visitor_pass_module():
    mod_path = (
        Path(__file__).resolve().parents[1]
        / "agent_workspace"
        / "03_tools"
        / "plugins"
        / "smartserva_visitor_pass"
        / "main.py"
    )
    spec = importlib.util.spec_from_file_location("smartserva_create_visitor_pass", mod_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load create_visitor_pass module")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


class SmartServaVisitorPickTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._cvp = _load_create_visitor_pass_module()

    def test_pick_newest_same_display_name_uses_highest_id(self):
        rows = [
            ("100", "Kommu", "Expired"),
            ("205", "Kommu", "Approved"),
            ("99", "Kommu", "Old"),
        ]
        out = self._cvp.pick_newest_matching_visitor(rows, "Kommu")
        self.assertEqual(out, ("205", "Approved"))

    def test_pick_newest_no_match(self):
        self.assertIsNone(self._cvp.pick_newest_matching_visitor([("1", "Other", "X")], "Kommu"))


if __name__ == "__main__":
    unittest.main()
