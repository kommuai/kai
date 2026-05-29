import unittest

from kai.support_runtime.vehicle_intent import is_catalog_list_query, should_prefetch_vehicle_support


class VehicleIntentTests(unittest.TestCase):
    def test_catalog_list_queries(self) -> None:
        self.assertTrue(is_catalog_list_query("list all supported cars"))
        self.assertTrue(is_catalog_list_query("what cars do you support"))
        self.assertFalse(is_catalog_list_query("how much is kommuassist"))

    def test_prefetch_brand_year(self) -> None:
        self.assertTrue(should_prefetch_vehicle_support("Proton X60 2024 supported?"))
        self.assertTrue(should_prefetch_vehicle_support("is toyota alphard 2020 supported"))

    def test_prefetch_list(self) -> None:
        self.assertTrue(should_prefetch_vehicle_support("list all supported vehicles"))

    def test_skip_pricing(self) -> None:
        self.assertFalse(should_prefetch_vehicle_support("how much is rent to own"))


if __name__ == "__main__":
    unittest.main()
