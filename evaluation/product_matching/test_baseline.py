"""Regression tests for W1-25 exact-ID and variant matching safeguards."""
import unittest

from baseline import match_products, normalize_gtin


class MatchTests(unittest.TestCase):
    def setUp(self):
        self.base = {
            "brand": "Sony", "model":"WH-1000XM5", "gtin":None,
            "mpn":"ABC-5-BLK", "variants":{"color":"Black","condition":"new"}
        }

    def test_gtin_checksum(self):
        self.assertEqual(normalize_gtin("2900000000018"), "02900000000018")
        self.assertIsNone(normalize_gtin("2900000000019"))

    def test_matching_mpn_with_brand(self):
        result = match_products(self.base, {**self.base,"model":"WH1000XM5"})
        self.assertEqual(result.decision, "match")

    def test_variant_conflict_prevents_match(self):
        other={**self.base,"variants":{"color":"Black","condition":"refurbished"}}
        self.assertEqual(match_products(self.base,other).decision,"non_match")

    def test_model_conflict_prevents_match(self):
        self.assertEqual(match_products(self.base,{**self.base,"model":"WH-1000XM4"}).decision,"non_match")

    def test_brand_conflict_prevents_match(self):
        self.assertEqual(match_products(self.base,{**self.base,"brand":"Bose"}).decision,"non_match")

    def test_title_and_price_are_not_product_identity(self):
        other={**self.base,"title":"Sony Wireless Headphones","price_usd":12}
        self.assertEqual(match_products(self.base,other).decision,"match")

    def test_identifier_missing_uses_attributes(self):
        first={**self.base,"mpn":None}
        second={**first,"model":"WH1000XM5"}
        self.assertEqual(match_products(first,second).evidence,"attributes")

    def test_incomplete_variants_abstains(self):
        first={**self.base,"mpn":None}
        second={**first,"variants":{"condition":"new"}}
        self.assertEqual(match_products(first,second).decision,"uncertain")

    def test_conflicting_gtins_abstain(self):
        first={**self.base,"gtin":"2900000000018"}
        other={**first,"gtin":"2900000000025"}
        self.assertEqual(match_products(first,other).decision,"uncertain")

    def test_mpn_without_brand_is_insufficient(self):
        first={**self.base,"brand":None,"model":None}
        second={**first}
        self.assertEqual(match_products(first,second).decision,"uncertain")

    
    def test_accessory_not_matched_to_product(self):
        product = {
            **self.base,
            "mpn": None,
            "title": "Sony WH-1000XM5 Headphones"
        }

        accessory = {
            **product,
            "title": "Carrying Case Compatible with Sony WH-1000XM5"
        }

        result = match_products(product, accessory)

        self.assertEqual(result.decision, "non_match")
        self.assertEqual(result.evidence, "product_type_conflict")

    
    def test_title_ram_conflicts_with_structured_memory(self):
        product = {
            **self.base,
            "title": "Laptop with 16GB RAM",
            "model": "Example Laptop 1",
            "mpn": None,
            "variants": {
                "memory": "16GB",
                "condition": "new"
            }
        }

        inconsistent = {
            **product,
            "title": "Laptop with 8GB RAM"
        }

        result = match_products(product, inconsistent)

        self.assertNotEqual(result.decision, "match")

    
    def test_ram_and_ssd_are_not_confused(self):
        product_a = {
            **self.base,
            "title": "Laptop with 16GB RAM and 512GB SSD",
            "model": "Example Laptop 1",
            "gtin": None,
            "mpn": None,
            "variants": {
                "memory": "16GB",
                "storage": "512GB",
                "condition": "new"
            }
        }

        product_b = {
            **product_a,
            "title": "Laptop 512GB SSD with 16GB RAM"
        }

        result = match_products(product_a, product_b)

        self.assertEqual(result.decision, "match")

    
    def test_title_storage_conflicts_with_structured_storage(self):
        product_a = {
            "brand": "Samsung",
            "model": "Galaxy S24",
            "gtin": None,
            "mpn": None,
            "title": "Samsung Galaxy S24 256GB Black",
            "variants": {
                "storage": "128GB",
                "color": "Black",
                "condition": "new"
            }
        }

        product_b = {
            **product_a,
            "title": "Samsung Galaxy S24 128GB Black"
        }

        result = match_products(product_a, product_b)

        self.assertEqual(result.decision, "uncertain")


    




if __name__ == "__main__":
    unittest.main()
