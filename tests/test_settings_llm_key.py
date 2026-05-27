"""Regression: empty KAI_LLM_API_KEY must not shadow DEEPSEEK_API_KEY.

Before the harness refactor only DEEPSEEK_API_KEY was set in env. After the
refactor a template `.env` introduced an explicit `KAI_LLM_API_KEY=` (empty),
which silently won the lookup and left the provider unauthenticated -- the
ReAct loop then returned empty strings and the channel `no_signal` clarify
text was sent for every question.
"""

from __future__ import annotations

import os
import unittest

from kai.settings import reload_settings


class LLMApiKeyFallbackTests(unittest.TestCase):
    def setUp(self) -> None:
        self._snapshot = {
            "KAI_LLM_API_KEY": os.environ.get("KAI_LLM_API_KEY"),
            "DEEPSEEK_API_KEY": os.environ.get("DEEPSEEK_API_KEY"),
        }

    def tearDown(self) -> None:
        for key, value in self._snapshot.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        reload_settings()

    def test_empty_kai_llm_api_key_falls_back_to_deepseek(self) -> None:
        os.environ["KAI_LLM_API_KEY"] = ""
        os.environ["DEEPSEEK_API_KEY"] = "sk-test-deepseek"
        settings = reload_settings()
        self.assertEqual(settings.kai_llm_api_key, "sk-test-deepseek")
        self.assertEqual(settings.deepseek_api_key, "sk-test-deepseek")

    def test_unset_kai_llm_api_key_falls_back_to_deepseek(self) -> None:
        os.environ.pop("KAI_LLM_API_KEY", None)
        os.environ["DEEPSEEK_API_KEY"] = "sk-test-deepseek-2"
        settings = reload_settings()
        self.assertEqual(settings.kai_llm_api_key, "sk-test-deepseek-2")

    def test_kai_llm_api_key_wins_when_both_set(self) -> None:
        os.environ["KAI_LLM_API_KEY"] = "sk-kai-primary"
        os.environ["DEEPSEEK_API_KEY"] = "sk-deepseek-secondary"
        settings = reload_settings()
        self.assertEqual(settings.kai_llm_api_key, "sk-kai-primary")

    def test_both_empty_means_no_key(self) -> None:
        os.environ["KAI_LLM_API_KEY"] = ""
        os.environ["DEEPSEEK_API_KEY"] = ""
        settings = reload_settings()
        self.assertEqual(settings.kai_llm_api_key, "")


if __name__ == "__main__":
    unittest.main()
