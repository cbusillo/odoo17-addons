from unittest.mock import patch
from odoo.tests.common import TransactionCase


class TestProductImport(TransactionCase):
    def setUp(self):
        super().setUp()
        self.product_import_model = self.env["product.import"]

    @patch("odoo.addons.product_connect.models.product_import.ProductImport.print_product_labels")
    def test_create(self, mock_print_product_labels):
        vals = {"default_code": "New", "mpn": "MPN001", "condition": "used", "quantity": 1}
        product = self.product_import_model.create(vals)

        self.assertGreaterEqual(int(product.default_code), 8000)
        self.assertLessEqual(int(product.default_code), 1000000)
        self.assertEqual(product.mpn, "MPN001")
        self.assertEqual(product.condition, "used")
        self.assertEqual(product.quantity, 1)

        mock_print_product_labels.assert_called_once()

    @patch("odoo.addons.product_connect.models.product_import.ProductImport.print_product_labels")
    def test_write(self, mock_print_product_labels):
        # create a product first
        vals = {"default_code": "New", "condition": "used", "quantity": 1}
        product = self.product_import_model.create(vals)

        # modify the product with write()
        update_vals = {"mpn": "MPN002", "quantity": 2}
        product.write(update_vals)

        # check that default_code is a 6-digit number in the correct range
        self.assertGreaterEqual(int(product.default_code), 8000)
        self.assertLessEqual(int(product.default_code), 1000000)

        self.assertEqual(product.mpn, "MPN002")
        self.assertEqual(product.quantity, 2)

        mock_print_product_labels.assert_called_once()
