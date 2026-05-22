import unittest
from unittest.mock import patch

from kai.support_runtime.agent_tools import AgentToolRegistry
from kai.support_runtime.retrieval import HybridRetriever, SimpleReranker


class VehicleSupportEvidenceTests(unittest.TestCase):
    @patch(
        "kai.support_runtime.tools.site_search.support_site_corpus",
        return_value="Perodua Myvi (2022-2026 AV) listed with ACC and LKA",
    )
    def test_official_site_search_returns_results(self, _support):
        reg = AgentToolRegistry(HybridRetriever(provider=None), SimpleReranker(provider=None))
        out = reg.call("search_kommu_support", {"query": "Myvi 2024 support"})
        self.assertTrue(out["ok"])
        self.assertIn("results", out)
        self.assertGreaterEqual(len(out["results"]), 1)

    @patch("kai.settings.get_settings")
    def test_web_search_handles_missing_key(self, mock_settings):
        mock_settings.return_value.bing_api_key = ""
        reg = AgentToolRegistry(HybridRetriever(provider=None), SimpleReranker(provider=None))
        out = reg.call("search_web", {"query": "Mazda 3 ACC LKA specs"})
        self.assertFalse(out["ok"])
        self.assertEqual(out["error"], "missing_bing_api_key")


if __name__ == "__main__":
    unittest.main()
