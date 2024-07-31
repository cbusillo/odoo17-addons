import json
import logging
import sys
import unittest
from typing import Optional

import black
import requests
from odoo.tests import common, tagged, BaseCase
from requests import Response, Session, PreparedRequest
from sgqlc.operation import Operation

_logger = logging.getLogger(__name__)


class TestShopifySettingsMixin(unittest.TestCase):
    client: Optional["odoo.model.shopify_client"] = None

    def test_1settings(self) -> None:
        self.client._overwrite_settings_from_dotenv()
        try:
            self.assertTrue(self.client.store_url_key)
            self.assertIn("myshopify.com", self.client.store_url)
            self.assertIn("shpat_", self.client.api_token)
            self.assertIn("-", self.client.api_version)
            self.assertIn("graphql.json", self.client.endpoint_url)
            self.assertTrue(self.client.endpoint_url.startswith("https://"))
            self.assertIn(self.client.store_url, self.client.endpoint_url)
        except AssertionError as e:
            _logger.error("Exiting due to test credentials not loading")
            _logger.error(e)

            sys.exit(1)


class TestShopifyClientBase(common.HttpCase, TestShopifySettingsMixin):
    client: Optional["odoo.model.shopify_client"] = None
    shopify_schema = None

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.client = cls.env["shopify.client"].with_context(use_dotenv=True).create({})
        from odoo.addons.product_connect.services.generated.shopify import shopify_schema

        cls.shopify_schema = shopify_schema


class TestShopifyClientBaseExternal(TestShopifyClientBase):
    _super_send = requests.Session.send

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()

        cls.original_request_handler = BaseCase._request_handler

        def patched_request_handler(session: Session, request: PreparedRequest, **kwargs) -> Response:
            if cls.client.endpoint_url == request.url:
                return cls._super_send(self=session, request=request, **kwargs)
            return cls.original_request_handler(session, request, **kwargs)

        BaseCase._request_handler = patched_request_handler


@tagged("post_install", "-at_install", "shopify")
class TestShopifyClientInternal(TestShopifyClientBase):

    def test_client_creation(self) -> None:
        self.assertTrue(self.client)


@tagged("post_install", "-at_install", "shopify", "current")
class TestShopifyClientExternal(TestShopifyClientBaseExternal):
    def test_execute_query(self) -> None:
        _logger.info(f"Available attributes in shopify module: {dir(self.shopify_schema)}")

        op = Operation(self.shopify_schema.query_type)
        shop_query = op.shop()
        shop_query.name()
        shop_query.description()
        shop_query.primary_domain()
        shop_query.primary_domain().host()
        shop_query.primary_domain().url()

        shop_data = self.client.execute(op)
        shop = (op + shop_data).shop

        self.assertTrue(shop, "Shop data not found")
        self.assertIn("test", shop.name, "'test' not found in shop name")

        _logger.info(
            f"Shop name: {shop.name} - {shop.description} - {shop.primary_domain.host} - {shop.primary_domain.url}"
        )

    def test_execute_mutation(self) -> None:
        op = Operation(self.shopify_schema.mutation_type)

        # Define the input for creating a product
        product_input = self.shopify_schema.ProductInput(
            title="Test Product",
            description_html="<p>Test Description</p>",
            product_type="Test Type",
            vendor="Test Vendor",
        )

        # Use the productCreate mutation
        product_create = op.product_create(input=product_input)

        # Select fields from the response
        product = product_create.product
        product.id()
        product.title()
        product.description_html()
        product.product_type()
        product.vendor()
        product.status()
        variants = product.variants(first=1)
        variants.edges().node().price()
        variants.edges().node().sku()

        created_product_data = self.client.execute(op)

        # Extract the created product from the result
        created_product = (op + created_product_data).product_create.product

        # Assertions
        self.assertIsNotNone(created_product, "Product was not created")
        self.assertEqual(created_product.title, "Test Product", "Product title does not match")
        self.assertEqual(
            created_product.description_html, "<p>Test Description</p>", "Product description does not match"
        )
        self.assertEqual(created_product.product_type, "Test Type", "Product type does not match")
        self.assertEqual(created_product.vendor, "Test Vendor", "Product vendor does not match")
        self.assertTrue(len(created_product.variants.edges) > 0, "No variants were created")
        self.assertEqual(created_product.variants.edges[0].node.price, "10.00", "Product price does not match")

        _logger.info(
            f"Product created: {created_product.title} - {created_product.description_html} - {created_product.variants[0].edges[0].nodes[0].price}"
        )


@tagged("post_install", "-at_install", "shopify", "slow")
class TestShopifyClientExternalSlow(TestShopifyClientBaseExternal):
    def test_generate_schema(self) -> None:
        schema_path = self.client._get_current_schema_path()
        schema_path.unlink(missing_ok=True)
        self.assertFalse(schema_path.exists(), f"Schema file not removed: {schema_path}")
        self.client._generate_schema()
        self.assertTrue(schema_path.exists(), f"Schema file not generated: {schema_path}")
        self.assertTrue(schema_str := schema_path.read_text(), "Schema file is empty")
        self.assertTrue(schema_data := json.loads(schema_str), "Schema file contains invalid JSON")
        self.assertTrue(
            types := schema_data.get("data", {}).get("__schema", {}).get("types"),
            "Schema file is missing data or types",
        )
        self.assertTrue(len(types) > 0, "Schema file has no types")
        self.assertFalse(json.loads(schema_path.read_text()).get("errors"), "Schema file contains errors")
        _logger.info(types[:10])

    def test_for_generate_module(self) -> None:
        model_path = self.client._get_current_models_path()
        model_path.unlink(missing_ok=True)
        self.assertFalse(model_path.exists(), f"Module file not removed: {model_path}")
        self.client._generate_models()
        self.assertTrue(model_path.exists(), f"Module file not generated: {model_path}")
        self.assertTrue(model_path.read_text(), "Module file is empty")
        self.assertTrue(model_path.stat().st_size > 1024 * 1024, "Module file is too small")
        self.assertTrue(
            black.format_file_in_place(
                model_path,
                fast=True,
                mode=black.FileMode(),
                write_back=black.WriteBack.CHECK,
            ),
            "Module file is not formatted correctly",
        )
