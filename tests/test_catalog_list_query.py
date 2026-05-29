import unittest
from unittest.mock import patch

from kai.support_runtime.tools.site_search import catalog_list_result, is_catalog_list_query


class CatalogListQueryTests(unittest.TestCase):
    @patch(
        "kai.support_runtime.tools.site_search._load_vehicle_catalog",
        return_value=[
            {"name": "Proton S70", "years": {2023, 2024}, "search_words": set(), "model_words": set()},
            {"name": "Toyota Alphard", "years": {2020}, "search_words": set(), "model_words": set()},
        ],
    )
    def test_list_returns_catalog_summary(self, _mock: object) -> None:
        self.assertTrue(is_catalog_list_query("list all supported cars"))
        out = catalog_list_result(vehicles_json_url="http://example/catalog.json")
        self.assertTrue(out and out.get("ok"))
        self.assertTrue(out.get("catalog_list"))
        text = out["results"][0]["text"]
        self.assertIn("Proton S70", text)
        self.assertIn("Toyota Alphard", text)
        self.assertNotIn("is **not** on the official", text)


if __name__ == "__main__":
    unittest.main()
