"""Comprehensive tests for _match_official_vehicle covering all 32 vehicles.

Tests brand+model, model-only, brand+model+year, variant-bearing, alias,
and year-out-of-range negative cases.
"""
from __future__ import annotations

import unittest
from unittest.mock import patch

from kai.support_runtime.tools.site_search import (
    _expand_years,
    _normalize_vehicle_query,
    match_vehicle_catalog,
)

RAW_VEHICLES = [
    {"brand": "Perodua", "model": "Alza", "year": "2022-2026", "variant": "AV"},
    {"brand": "Perodua", "model": "Ativa", "year": "2019-2026", "variant": "AV"},
    {"brand": "Perodua", "model": "Myvi", "year": "2022-2026", "variant": "AV"},
    {"brand": "Proton", "model": "S70", "year": "2024-2026", "variant": "Flagship, Flagship X"},
    {"brand": "Proton", "model": "X50", "year": "2019-2024", "variant": "Flagship"},
    {"brand": "Proton", "model": "X50 FL", "year": "2025-2026", "variant": "Premium, Flagship"},
    {"brand": "Proton", "model": "X70 FL", "year": "2024-2026", "variant": "Premium, Premium X"},
    {"brand": "Proton", "model": "X90", "year": "2024-2026", "variant": "Premium, Flagship"},
    {"brand": "Honda", "model": "Accord", "year": "2023-2025", "variant": "All"},
    {"brand": "Honda", "model": "City", "year": "2021-2023", "variant": "V-Sensing, RS Hybrid"},
    {"brand": "Honda", "model": "City FL", "year": "2023-2026", "variant": "RS Hybrid"},
    {"brand": "Honda", "model": "Civic", "year": "2022-2026", "variant": "All"},
    {"brand": "Honda", "model": "CRV Gen 5", "year": "2016-2023", "variant": "All"},
    {"brand": "Honda", "model": "HRV", "year": "2023-2026", "variant": "All"},
    {"brand": "Toyota", "model": "Alphard", "year": "2019-2022", "variant": "2.5V, Hybrid"},
    {"brand": "Toyota", "model": "Camry", "year": "2018-2024", "variant": "V, Hybrid"},
    {"brand": "Toyota", "model": "Corolla Altis", "year": "2020-2024", "variant": "G, Hybrid"},
    {"brand": "Toyota", "model": "Corolla Cross", "year": "2022-2026", "variant": "V, Hybrid"},
    {"brand": "Toyota", "model": "Harrier", "year": "2022-2023", "variant": "All"},
    {"brand": "Toyota", "model": "Innova Zenix", "year": "2024-2026", "variant": "All"},
    {"brand": "Toyota", "model": "Veloz", "year": "2022-2026", "variant": "AT"},
    {"brand": "Toyota", "model": "Vios", "year": "2023-2026", "variant": "G"},
    {"brand": "Lexus", "model": "ES", "year": "2019-2022", "variant": "All"},
    {"brand": "Lexus", "model": "NX", "year": "2020-2022", "variant": "All"},
    {"brand": "Lexus", "model": "UX", "year": "2020-2022", "variant": "All"},
    {"brand": "Lexus", "model": "RX", "year": "2020-2022", "variant": "All"},
    {"brand": "BYD", "model": "Atto 3", "year": "2023-2026", "variant": "All"},
    {"brand": "BYD", "model": "Atto 3 Ultra", "year": "2025-2026", "variant": "All"},
    {"brand": "BYD", "model": "Dolphin", "year": "2023-2026", "variant": "All"},
    {"brand": "BYD", "model": "M6", "year": "2025-2026", "variant": "Extended"},
    {"brand": "BYD", "model": "Seal", "year": "2024-2026", "variant": "All"},
    {"brand": "BYD", "model": "Sealion 7", "year": "2025-2026", "variant": "All"},
]


def _build_fixture() -> list[dict]:
    rows = []
    for raw in RAW_VEHICLES:
        brand = raw["brand"]
        model = raw["model"]
        variant = raw["variant"]
        years = _expand_years(raw["year"])
        search_text = _normalize_vehicle_query(f"{brand} {model} {variant}")
        search_words = set(search_text.split())
        model_words = set(model.lower().split())
        rows.append({
            "name": f"{brand} {model}",
            "brand": brand,
            "model": model,
            "years": years,
            "variant": variant,
            "search_words": search_words,
            "model_words": model_words,
        })
    return rows


FIXTURE = _build_fixture()


def _patched_match(query: str):
    """Run vehicle matcher with fixture catalog."""
    with patch(
        "kai.support_runtime.tools.site_search._load_vehicle_catalog",
        return_value=FIXTURE,
    ):
        return match_vehicle_catalog(query, vehicles_json_url="test-fixture", timeout=1)


class TestBrandModelQuery(unittest.TestCase):
    """Every vehicle must match on 'brand model'."""

    CASES = [
        ("perodua alza", "Alza"),
        ("perodua ativa", "Ativa"),
        ("perodua myvi", "Myvi"),
        ("proton s70", "S70"),
        ("proton x50", "X50"),
        ("proton x50 fl", "X50 FL"),
        ("proton x70 fl", "X70 FL"),
        ("proton x90", "X90"),
        ("honda accord", "Accord"),
        ("honda city", "City"),
        ("honda city fl", "City FL"),
        ("honda civic", "Civic"),
        ("honda crv gen 5", "CRV Gen 5"),
        ("honda hrv", "HRV"),
        ("toyota alphard", "Alphard"),
        ("toyota camry", "Camry"),
        ("toyota corolla altis", "Corolla Altis"),
        ("toyota corolla cross", "Corolla Cross"),
        ("toyota harrier", "Harrier"),
        ("toyota innova zenix", "Innova Zenix"),
        ("toyota veloz", "Veloz"),
        ("toyota vios", "Vios"),
        ("lexus es", "ES"),
        ("lexus nx", "NX"),
        ("lexus ux", "UX"),
        ("lexus rx", "RX"),
        ("byd atto 3", "Atto 3"),
        ("byd atto 3 ultra", "Atto 3 Ultra"),
        ("byd dolphin", "Dolphin"),
        ("byd m6", "M6"),
        ("byd seal", "Seal"),
        ("byd sealion 7", "Sealion 7"),
    ]

    def test_brand_model_matches(self):
        for query, expected_model in self.CASES:
            with self.subTest(query=query):
                result = _patched_match(query)
                self.assertIsNotNone(result, f"'{query}' should match")
                self.assertEqual(result["model"], expected_model)


class TestModelOnlyQuery(unittest.TestCase):
    """Model-only queries should match (single-token model names)."""

    CASES = [
        ("alza", "Alza"),
        ("ativa", "Ativa"),
        ("myvi", "Myvi"),
        ("s70", "S70"),
        ("x50", "X50"),
        ("x90", "X90"),
        ("accord", "Accord"),
        ("civic", "Civic"),
        ("hrv", "HRV"),
        ("alphard", "Alphard"),
        ("camry", "Camry"),
        ("harrier", "Harrier"),
        ("veloz", "Veloz"),
        ("vios", "Vios"),
        ("dolphin", "Dolphin"),
        ("m6", "M6"),
        ("seal", "Seal"),
    ]

    def test_model_only_matches(self):
        for query, expected_model in self.CASES:
            with self.subTest(query=query):
                result = _patched_match(query)
                self.assertIsNotNone(result, f"model-only '{query}' should match")
                self.assertEqual(result["model"], expected_model)


class TestBrandModelYearQuery(unittest.TestCase):
    """Brand+model+year within range should match."""

    CASES = [
        ("perodua alza 2024", "Alza"),
        ("perodua myvi 2023", "Myvi"),
        ("proton s70 2025", "S70"),
        ("honda civic 2024", "Civic"),
        ("honda crv gen 5 2020", "CRV Gen 5"),
        ("toyota alphard 2021", "Alphard"),
        ("toyota corolla cross 2025", "Corolla Cross"),
        ("lexus es 2020", "ES"),
        ("lexus nx 2021", "NX"),
        ("byd atto 3 2024", "Atto 3"),
        ("byd dolphin 2025", "Dolphin"),
        ("byd seal 2025", "Seal"),
        ("byd m6 2025", "M6"),
        ("byd sealion 7 2026", "Sealion 7"),
    ]

    def test_brand_model_year_matches(self):
        for query, expected_model in self.CASES:
            with self.subTest(query=query):
                result = _patched_match(query)
                self.assertIsNotNone(result, f"'{query}' should match")
                self.assertEqual(result["model"], expected_model)


class TestVariantBearingQuery(unittest.TestCase):
    """Queries mentioning variant keywords should still match correctly."""

    CASES = [
        ("honda city rs hybrid", "City"),
        ("honda city fl rs hybrid", "City FL"),
        ("proton s70 flagship", "S70"),
        ("proton x50 fl premium", "X50 FL"),
        ("proton x70 fl premium x", "X70 FL"),
        ("proton x90 flagship", "X90"),
        ("toyota camry hybrid", "Camry"),
        ("toyota corolla altis hybrid", "Corolla Altis"),
        ("toyota corolla cross hybrid", "Corolla Cross"),
        ("toyota alphard hybrid", "Alphard"),
        ("byd m6 extended", "M6"),
    ]

    def test_variant_queries(self):
        for query, expected_model in self.CASES:
            with self.subTest(query=query):
                result = _patched_match(query)
                self.assertIsNotNone(result, f"variant query '{query}' should match")
                self.assertEqual(result["model"], expected_model)


class TestYearOutOfRangeNegative(unittest.TestCase):
    """Year outside the vehicle's supported range should NOT match."""

    CASES = [
        ("perodua myvi 2018", "Myvi"),
        ("proton s70 2023", "S70"),
        ("honda civic 2018", "Civic"),
        ("honda crv gen 5 2025", "CRV Gen 5"),
        ("toyota alphard 2025", "Alphard"),
        ("lexus es 2025", "ES"),
        ("byd atto 3 2022", "Atto 3"),
        ("byd dolphin 2020", "Dolphin"),
        ("byd seal 2023", "Seal"),
        ("byd m6 2024", "M6"),
        ("byd sealion 7 2024", "Sealion 7"),
    ]

    def test_year_out_of_range_returns_none(self):
        for query, label in self.CASES:
            with self.subTest(query=query):
                result = _patched_match(query)
                self.assertIsNone(result, f"'{query}' should be None (year out of range for {label})")


class TestAliasQueries(unittest.TestCase):
    """Common alternate spellings and hyphenated forms should match."""

    CASES = [
        ("honda cr-v", "CRV Gen 5"),
        ("honda hr-v", "HRV"),
        ("byd atto3", "Atto 3"),
        ("byd sealion7", "Sealion 7"),
        ("proton x50fl", "X50 FL"),
        ("proton x70fl", "X70 FL"),
        ("honda cityfl", "City FL"),
    ]

    def test_alias_matches(self):
        for query, expected_model in self.CASES:
            with self.subTest(query=query):
                result = _patched_match(query)
                self.assertIsNotNone(result, f"alias query '{query}' should match")
                self.assertEqual(result["model"], expected_model)


class TestSealVsSealionNoFalsePositive(unittest.TestCase):
    """'seal' must not match 'Sealion 7' and vice versa."""

    def test_seal_matches_seal_not_sealion(self):
        result = _patched_match("byd seal")
        self.assertIsNotNone(result)
        self.assertEqual(result["model"], "Seal")

    def test_sealion_matches_sealion_not_seal(self):
        result = _patched_match("byd sealion 7")
        self.assertIsNotNone(result)
        self.assertEqual(result["model"], "Sealion 7")


class TestBrandOnlyDoesNotMatchSingle(unittest.TestCase):
    """A brand name alone (no model token) should NOT match since min_hits=2."""

    CASES = ["honda", "toyota", "perodua", "proton", "lexus", "byd"]

    def test_brand_only_returns_none(self):
        for brand in self.CASES:
            with self.subTest(brand=brand):
                result = _patched_match(brand)
                self.assertIsNone(result, f"brand-only '{brand}' should not match")


class TestEmptyAndGarbage(unittest.TestCase):
    def test_empty(self):
        self.assertIsNone(_patched_match(""))

    def test_none(self):
        self.assertIsNone(_patched_match(None))

    def test_garbage(self):
        self.assertIsNone(_patched_match("asdfghjkl xyz123"))


if __name__ == "__main__":
    unittest.main()
