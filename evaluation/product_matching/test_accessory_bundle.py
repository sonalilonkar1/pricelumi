"""W1-25 review #2: product/accessory/bundle regression tests."""
import unittest

from baseline import is_accessory, is_bundle, match_products


class AccessoryBundleReviewTests(unittest.TestCase):
    def setUp(self):
        self.offer = {
            "title": "Sony WH-1000XM5 wireless headphones",
            "brand": "Sony",
            "model": "WH-1000XM5",
            "gtin": "2900000000018",  # Synthetic checksum-valid test identifier.
            "mpn": "SYN-XM5",
            "variants": {"color": "Black", "condition": "new"},
        }

    def with_title(self, title):
        return {**self.offer, "title": title}

    def test_screen_protector_is_accessory(self):
        phone = {**self.offer, "brand": "Samsung", "model": "Galaxy S24",
                 "title": "Samsung Galaxy S24 256GB",
                 "variants": {"storage": "256GB", "condition": "new"}}
        accessory = {**phone, "title": "Screen protector compatible with Samsung Galaxy S24"}
        self.assertTrue(is_accessory(accessory))
        self.assertEqual(match_products(phone, accessory).decision, "non_match")

    def test_replacement_charger_is_accessory(self):
        accessory = self.with_title("Replacement charger for Sony WH-1000XM5")
        self.assertTrue(is_accessory(accessory))
        self.assertEqual(match_products(self.offer, accessory).evidence, "product_type_conflict")

    def test_watch_strap_is_accessory(self):
        watch = {**self.offer, "brand": "Apple", "model": "Watch Series 9",
                 "title": "Apple Watch Series 9"}
        accessory = {**watch, "title": "Watch strap for Apple Watch Series 9"}
        self.assertTrue(is_accessory(accessory))
        self.assertEqual(match_products(watch, accessory).decision, "non_match")

    def test_bundle_with_protective_case_not_confused_with_accessory(self):
        bundle = self.with_title("Sony WH-1000XM5 headphones bundle with protective case")
        self.assertTrue(is_bundle(bundle))
        self.assertFalse(is_accessory(bundle))
        self.assertEqual(match_products(self.offer, bundle).evidence, "bundle_conflict")

    def test_with_carrying_case_is_bundle(self):
        bundle = self.with_title("Sony WH-1000XM5 headphones with carrying case")
        self.assertTrue(is_bundle(bundle))
        self.assertEqual(match_products(self.offer, bundle).decision, "uncertain")

    def test_multi_pack_is_bundle(self):
        bundle = self.with_title("Sony WH-1000XM5 headphones 2-pack")
        self.assertTrue(is_bundle(bundle))
        self.assertEqual(match_products(self.offer, bundle).decision, "uncertain")

    def test_two_bundles_do_not_match_without_contents(self):
        first = self.with_title("Sony WH-1000XM5 headphones bundle with protective case")
        second = self.with_title("Sony WH-1000XM5 headphones starter kit")
        self.assertEqual(match_products(first, second).evidence, "bundle_contents_unverified")

    def test_regular_headphones_are_not_bundle_or_accessory(self):
        plain = self.with_title("Sony WH-1000XM5 headphones with noise cancellation")
        self.assertFalse(is_accessory(plain))
        self.assertFalse(is_bundle(plain))
        self.assertEqual(match_products(self.offer, plain).decision, "match")


if __name__ == "__main__":
    unittest.main()
