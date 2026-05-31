import unittest

from shadou.support_runtime.agent_context import (
    ALLOWED_CONTEXT_SOURCES,
    SOURCE_POLICY_PREAMBLE,
    build_agent_system_prompt,
)


class AgentSourcePolicyTests(unittest.TestCase):
    def test_allowed_sources_tuple_is_stable(self) -> None:
        self.assertEqual(
            ALLOWED_CONTEXT_SOURCES,
            ("workspace_settings", "system_prompt", "master_faq", "tools", "session_clock"),
        )

    def test_system_prompt_includes_policy_preamble(self) -> None:
        prompt = build_agent_system_prompt([{"name": "search_faq", "description": "Search FAQ"}])
        self.assertIn(SOURCE_POLICY_PREAMBLE[:40], prompt)
        self.assertIn("Agent source policy", prompt)
        self.assertIn("search_faq", prompt)
        self.assertNotIn("learnt_faq", prompt.lower())


if __name__ == "__main__":
    unittest.main()
