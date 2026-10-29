"""Regression tests for incomplete variants on identifier match paths."""
import unittest

from baseline import match_products


class IncompleteVariantPolicyTests(unittest.TestCase):
    def setUp(self):
        self.offer = {
            "brand": "Sony",
            "model": "WH-1000XM5",
            "gtin": "2900000000018",  # synthetic, checksum-valid
            "mpn": "SYN-WH1000XM5-BLK",
            "variants": {"color": "Black", "condition": "new"},
        }

    def test_same_gtin_missing_condition_is_uncertain(self):
        other = {**self.offer, "variants": {"color": "Black"}}
        result = match_products(self.offer, other)
        self.assertEqual(result.decision, "uncertain")
        self.assertEqual(result.evidence, "missing_variant")

    def test_same_mpn_missing_storage_is_uncertain(self):
        original = {**self.offer, "gtin": None, "variants": {"storage": "256GB", "condition": "new"}}
        other = {**original, "variants": {"condition": "new"}}
        result = match_products(original, other)
        self.assertEqual(result.decision, "uncertain")
        self.assertEqual(result.evidence, "missing_variant")

    def test_same_gtin_complete_attributes_still_match(self):
        other = {**self.offer, "title": "Sony XM5 headphones - black"}
        self.assertEqual(match_products(self.offer, other).decision, "match")

    def test_same_gtin_explicit_condition_disagreement_is_nonmatch(self):
        other = {**self.offer, "variants": {"color": "Black", "condition": "used"}}
        self.assertEqual(match_products(self.offer, other).decision, "non_match")

    def test_same_gtin_missing_color_is_uncertain(self):
        other = {**self.offer, "variants": {"condition": "new"}}
        self.assertEqual(match_products(self.offer, other).decision, "uncertain")


if __name__ == "__main__":
    unittest.main()
