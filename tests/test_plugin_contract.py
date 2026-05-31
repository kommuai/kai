import unittest

from shadou.tools_plugins.contract import (
    normalize_tool_result,
    tool_failure_observation_message,
    validate_plugin_source,
)
from pathlib import Path

PLUGIN_TEMPLATE = (Path(__file__).resolve().parents[1] / "templates/workspace/generic/tools/plugins/example_plugin/main.py").read_text(
    encoding="utf-8"
)


class PluginContractTests(unittest.TestCase):
    def test_template_passes_contract(self) -> None:
        self.assertEqual([], validate_plugin_source(PLUGIN_TEMPLATE, plugin_id="template"))

    def test_forbids_stdin_json(self) -> None:
        bad = 'import json, sys\njson.load(sys.stdin)\nprint(json.dumps({"ok": True}))'
        errs = validate_plugin_source(bad)
        self.assertTrue(any("stdin" in e.lower() for e in errs))

    def test_normalize_missing_ok(self) -> None:
        out = normalize_tool_result({"data": 1})
        self.assertFalse(out["ok"])
        self.assertIn("missing_ok", out["error"])

    def test_tool_failure_message_includes_error(self) -> None:
        msg = tool_failure_observation_message("create_visitor_pass", {"ok": False, "error": "bad_time"})
        self.assertIn("bad_time", msg)
        self.assertIn("ok: false", msg.lower())


if __name__ == "__main__":
    unittest.main()
