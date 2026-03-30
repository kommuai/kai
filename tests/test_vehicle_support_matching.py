import unittest

from services.kai_service import _extract_support_evidence


class VehicleSupportMatchingTests(unittest.TestCase):
    def test_extract_support_evidence_matches_model_and_year(self):
        corpus = (
            "Toyota Alphard 2020-2023 (ACC + LKA) is supported. "
            "Perodua Myvi 2022-2026 is supported."
        )
        out = _extract_support_evidence("Is Toyota Alphard 2020 supported?", corpus)
        self.assertIn("alphard", out.lower())
        self.assertIn("2020", out.lower())

    def test_extract_support_evidence_matches_interior_year_of_range(self):
        corpus = "Honda CRV Gen 5 2016-2023 All is supported."
        out = _extract_support_evidence("Is Honda CRV Gen 5 2017 supported?", corpus)
        self.assertIn("2016-2023", out)

    def test_extract_support_evidence_avoids_year_mismatch(self):
        corpus = "Toyota Alphard 2020-2023 is supported."
        out = _extract_support_evidence("Is Toyota Alphard 2018 supported?", corpus)
        self.assertEqual(out, "")


if __name__ == "__main__":
    unittest.main()
