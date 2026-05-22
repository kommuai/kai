import unittest
from unittest.mock import patch

from kai.support_runtime.agent_tools import AgentToolRegistry
from kai.support_runtime.retrieval import HybridRetriever, SimpleReranker


class VehicleSupportOfficialMatchTests(unittest.TestCase):
    @patch(
        "kai.support_runtime.agent_tools._official_supported_vehicles",
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
    def test_search_kommu_support_matches_alphard_2020(self, _mock_vehicles):
        reg = AgentToolRegistry(HybridRetriever(provider=None), SimpleReranker(provider=None))
        out = reg.call("search_kommu_support", {"query": "do you support toyota alphard 2020?"})
        self.assertTrue(out["ok"])
        self.assertTrue(out["results"])
        self.assertIn("Toyota Alphard", out["results"][0]["text"])
        self.assertIn("2019-2022", out["results"][0]["text"])


if __name__ == "__main__":
    unittest.main()
