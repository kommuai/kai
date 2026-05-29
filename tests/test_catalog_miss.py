import unittest

from kai.support_runtime.tools.site_search import catalog_miss_detail, format_catalog_miss_text, match_vehicle_catalog


class CatalogMissTests(unittest.TestCase):
    def test_proton_x60_not_listed_with_same_brand_hints(self) -> None:
        url = "https://raw.githubusercontent.com/kommuai/bukapilot/snapshot/selfdrive/car/supported_vehicle.json"
        self.assertIsNone(match_vehicle_catalog("Proton X60", vehicles_json_url=url))
        miss = catalog_miss_detail("Proton X60", vehicles_json_url=url)
        self.assertIsNotNone(miss)
        assert miss is not None
        self.assertFalse(miss["on_official_list"])
        self.assertTrue(miss["listed_same_brand"])
        text = format_catalog_miss_text(miss)
        self.assertIn("not", text.lower())
        self.assertIn("Proton", text)


if __name__ == "__main__":
    unittest.main()
