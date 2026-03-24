import unittest
from unittest.mock import patch

from support_runtime.tech_backlog import infer_possible_solution_from_bukapilot, summarize_issue


class TechBacklogEnrichmentTests(unittest.TestCase):
    def test_summarize_issue_adds_context_and_signals(self):
        out = summarize_issue(
            "KA2 keeps rebooting, error 1003 after update",
            product_class="KA2",
            recent_user_messages=["Still broken after SOP step 2", "Device restart loop"],
        )
        self.assertIn("Product=KA2", out)
        self.assertIn("Error codes=", out)
        self.assertIn("Recent context=", out)

    @patch(
        "support_runtime.tech_backlog.bukapilot_agentic_search",
        return_value={
            "ok": True,
            "branch": "release_ka2",
            "hits": [
                {
                    "path": "selfdrive/diagnostics/recovery.py",
                    "url": "https://github.com/bukapilot/bukapilot/blob/release_ka2/selfdrive/diagnostics/recovery.py",
                }
            ],
        },
    )
    def test_possible_solution_includes_file_link(self, _search):
        out = infer_possible_solution_from_bukapilot("KA2 error 1003 reboot loop")
        self.assertIn("release_ka2", out)
        self.assertIn("selfdrive/diagnostics/recovery.py", out)
        self.assertIn("https://github.com/bukapilot/bukapilot/blob/release_ka2", out)


if __name__ == "__main__":
    unittest.main()
