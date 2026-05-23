import tempfile
import unittest

from kai.workspace.tools_config import load_tools_config, reload_tools_config


class ToolProfileTests(unittest.TestCase):
    def test_profile_expands_when_tools_list_empty(self):
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
