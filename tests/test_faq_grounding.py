import unittest

from kai.support_runtime.faq_grounding import (
    FOOTNOTE_MARKER,
    apply_grounding_footnote_if_needed,
    is_answer_faq_grounded,
)


class FaqGroundingTests(unittest.TestCase):
    def test_faq_source_id_is_grounded(self):
        self.assertTrue(
            is_answer_faq_grounded(
                answer="Ship on Wed/Fri.",
                user_text="when ship",
                source_ids=["faq:shipping"],
            )
        )

    def test_ungrounded_gets_footnote(self):
        out = apply_grounding_footnote_if_needed(
            "We only ship within Malaysia and not to Indonesia.",
            user_text="ship to indonesia",
            lang="EN",
            source_ids=[],
            observations=[],
            retriever=None,
        )
        self.assertIn(FOOTNOTE_MARKER, out)

    def test_grounded_search_faq_observation_no_footnote(self):
        obs = [
            {
                "tool": "search_faq",
                "result": {
                    "ok": True,
                    "results": [
                        {
                            "source_id": "faq:international_shipping_regions",
                            "score": 0.9,
                            "text": "Q: ship\nA: Do not say Malaysia only.",
                            "metadata": {
                                "category": "known_faq_intent",
                                "intent_id": "international_shipping_regions",
                            },
                        }
                    ],
                },
            }
        ]
        out = apply_grounding_footnote_if_needed(
            "Do not say Malaysia only. Email support@kommu.ai.",
            user_text="ship to indonesia",
            lang="EN",
            source_ids=["tool:search_faq"],
            observations=obs,
            retriever=None,
        )
        self.assertNotIn(FOOTNOTE_MARKER, out)

    def test_grounded_tool_from_workspace_yaml(self) -> None:
        from kai.workspace.runtime_settings import reload_grounded_tools, reload_workspace_settings_yaml

        reload_workspace_settings_yaml()
        reload_grounded_tools()
        obs = [
            {
                "tool": "search_kommu_support",
                "result": {"ok": True, "on_official_list": False},
            }
        ]
        self.assertTrue(
            is_answer_faq_grounded(
                answer="Your car is not on the official list.",
                user_text="Proton X60",
                observations=obs,
            )
        )

    def test_chitchat_greeting_skips_footnote(self):
        out = apply_grounding_footnote_if_needed(
            "Hi! How can I help you with KommuAssist today?",
            user_text="hi",
            lang="EN",
            source_ids=[],
            skip_chitchat=True,
        )
        self.assertNotIn(FOOTNOTE_MARKER, out)


if __name__ == "__main__":
    unittest.main()
