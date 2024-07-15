from odoo.tests import common, tagged
from parameterized import parameterized


@tagged("post_install", "-at_install")
class TestShopifySync(common.TransactionCase):
    def setUp(self) -> None:
        super(TestShopifySync, self).setUp()
        self.shopify_sync = self.env["shopify.sync"]

    @parameterized.expand(
        [
            # Valid cases
            ("standard_format", "123456 - A01A1", "123456", "A01A1"),
            ("short_sku", "12345 - A01", "12345", "A01"),
            ("long_sku", "1234567 - A01A1", "1234567", "A01A1"),
            ("single_digit_sku", "1 - A01", "1", "A01"),
            ("single_char_bin", "123456 - A", "123456", "A"),
            ("numeric_bin", "123456 - 123", "123456", "123"),
            ("alphanumeric_bin", "123456 - A1B2C3", "123456", "A1B2C3"),
            ("space_instead_of_dash", "123456 A01A1", "123456", "A01A1"),
            # Edge cases
            ("leading_zeros_sku", "000123 - A01", "000123", "A01"),
            ("max_length_bin", "123456 - ABCDEF", "123456", "ABCDEF"),
            ("min_length_everything", "1 - A", "1", "A"),
            # Potential error cases (these should be handled gracefully)
            ("empty_sku", " - A01", "", "A01"),
            ("empty_bin", "123456 - ", "123456", ""),
            ("no_separator", "123456A01", "123456A01", ""),
            ("extra_spaces", "  123456  -  A01  ", "123456", "A01"),
            ("non_numeric_sku", "12A34B - A01", "12A34B", "A01"),
            ("bin_too_long", "123456 - A01A1B2", "123456", "A01A1B2"),
            ("special_chars_in_sku", "123-456 - A01", "123-456", "A01"),
            ("special_chars_in_bin", "123456 - A01-1", "123456", "A01-1"),
        ]
    )
    def test_extract_sku_bin_from_shopify_product(self, name, sku_input, expected_sku, expected_bin) -> None:
        product = {"id": f"gid://shopify/Product/{name}", "variants": {"edges": [{"node": {"sku": sku_input}}]}}

        sku, bin_location = self.shopify_sync.extract_sku_bin_from_shopify_product(product)

        self.assertEqual(sku, expected_sku, f"SKU mismatch for {name}")
        self.assertEqual(bin_location, expected_bin, f"BIN mismatch for {name}")
