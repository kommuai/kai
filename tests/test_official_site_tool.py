"""Builtin search_official_site — no tenant tool ids."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from shadou.support_runtime.agent_tools import AgentToolRegistry
from shadou.support_runtime.retrieval import HybridRetriever, SimpleReranker
from shadou.workspace.tools_config import reload_tools_config


class OfficialSiteToolTests(unittest.TestCase):
    def setUp(self) -> None:
        reload_tools_config()

    @patch("shadou.workspace.tools_config._profile_tool_ids")
    @patch(
        "shadou.support_runtime.tools.site_search._load_vehicle_catalog",
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


if __name__ == "__main__":
    unittest.main()
