"""Builtin search_official_site and search_web — no tenant tool ids."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from kai.support_runtime.agent_tools import AgentToolRegistry
from kai.support_runtime.retrieval import HybridRetriever, SimpleReranker
from kai.workspace.tools_config import reload_tools_config


class OfficialSiteToolTests(unittest.TestCase):
    def setUp(self) -> None:
        reload_tools_config()

    @patch("kai.workspace.tools_config._profile_tool_ids")
    @patch(
        "kai.support_runtime.tools.site_search._load_vehicle_catalog",
        return_value=[
            {
                "name": "Toyota Alphard",
                "brand": "Toyota",
                "model": "Alphard",
                "years": set(range(2019, 2023)),
                "variant": "2.5V, Hybrid",
                "search_words": {"toyota", "alphard", "2", "5v", "hybrid"},
                "model_words": {"alphard"},
            }
        ],
    )
    def test_search_official_site_matches_catalog_row(
        self, _mock_vehicles: object, mock_profile_ids: object
    ) -> None:
        mock_profile_ids.return_value = ["search_official_site"]
        reload_tools_config()
        reg = AgentToolRegistry(HybridRetriever(provider=None), SimpleReranker(provider=None))
        out = reg.call("search_official_site", {"query": "do you support toyota alphard 2020?"})
        self.assertTrue(out["ok"])
        self.assertTrue(out["results"])
        self.assertIn("Toyota Alphard", out["results"][0]["text"])

    @patch("kai.settings.get_settings")
    def test_web_search_handles_missing_key(self, mock_settings: object) -> None:
        mock_profile_ids_patch = patch(
            "kai.workspace.tools_config._profile_tool_ids",
            return_value=["search_web"],
        )
        with mock_profile_ids_patch:
            reload_tools_config()
            mock_settings.return_value.bing_api_key = ""
            reg = AgentToolRegistry(HybridRetriever(provider=None), SimpleReranker(provider=None))
            out = reg.call("search_web", {"query": "example ACC LKA specs"})
        self.assertFalse(out["ok"])
        self.assertEqual(out["error"], "missing_bing_api_key")


if __name__ == "__main__":
    unittest.main()
