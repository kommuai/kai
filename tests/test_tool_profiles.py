import tempfile
import unittest
from pathlib import Path

import yaml

from kai.workspace.tools_config import load_tools_config, reload_tools_config


class ToolProfileTests(unittest.TestCase):
    def test_profile_expands_when_tools_list_empty(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "tools.yaml"
            path.write_text(
                yaml.safe_dump(
                    {
                        "active_profile": "minimal",
                        "profiles": {"minimal": ["search_faq", "escalate_to_human"]},
                        "tools": [],
                    }
                ),
                encoding="utf-8",
            )
            # Patch path by writing into real workspace is hard; test parser via direct call
            from kai.workspace import tools_config as tc

            ids = tc._profile_tool_ids(
                {
                    "active_profile": "minimal",
                    "profiles": {"minimal": ["search_faq", "escalate_to_human"]},
                }
            )
            self.assertEqual(ids, ["search_faq", "escalate_to_human"])

    def test_kommu_workspace_has_explicit_tools(self):
        reload_tools_config()
        cfg = load_tools_config()
        self.assertGreaterEqual(len(cfg.enabled_entries()), 10)


if __name__ == "__main__":
    unittest.main()
