import logging
import sys
import time
import unittest
from unittest.mock import patch

import requests
from graphql import DocumentNode
from odoo.tests import common, tagged, BaseCase
from parameterized import parameterized
from requests import Response, Session, PreparedRequest

from odoo.addons.product_connect.services.shopify_client import ShopifyClientService

_logger = logging.getLogger(__name__)


class TestShopifyClientBase(common.HttpCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()

        cls.client = cls.env["shopify.client"].create({"from_dot_env": True})
        cls.config = cls.env["shopify.config"].get_config(from_dot_env=True)
        cls.client_service = ShopifyClientService(cls.env, from_dot_env=True)
        cls.shop_query_type = "store"
        cls.shop_query_name = "GetShop"

        cls.mock_send_request = "odoo.addons.product_connect.services.shopify_client.ShopifyClientService._send_request"
        if "testing" not in cls.client.endpoint_url.lower():
            _logger.error("Test will only run on testing environment")
            sys.exit(1)


class TestShopifyClientBaseExternal(TestShopifyClientBase):
    _super_send = requests.Session.send

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()

        cls.original_request_handler = BaseCase._request_handler

        def patched_request_handler(session: Session, request: PreparedRequest, **kwargs) -> Response:
            if "testing" not in cls.client.endpoint_url.lower():
                _logger.error("Test will only run on testing environment")
                sys.exit(1)
            if cls.client.endpoint_url == request.url:
                return cls._super_send(self=session, request=request, **kwargs)
            return cls.original_request_handler(session, request, **kwargs)

        BaseCase._request_handler = patched_request_handler

    def test_endpoint_url(self) -> None:
        self.assertTrue(self.client.endpoint_url)
        self.assertIn("myshopify.com", self.client.endpoint_url)
        self.assertIn("graphql.json", self.client.endpoint_url)
        self.assertTrue(self.client.endpoint_url.startswith("https://"))


@tagged("post_install", "-at_install", "shopify")
class TestShopifyClientInternal(TestShopifyClientBase):

    def test_settings(self) -> None:
        self.assertTrue(self.config.store_url_key)
        self.assertIn("myshopify.com", self.config.store_url)
        self.assertIn("shpat_", self.config.api_token)
        self.assertIn("-", self.config.api_version)
        self.assertIn("graphql.json", self.client.endpoint_url)
        self.assertTrue(self.client.endpoint_url.startswith("https://"))
        self.assertIn(self.config.store_url, self.client.endpoint_url)

    def test_get_client(self) -> None:
        self.assertTrue(self.client)

    def test_error_handling(self) -> None:
        with unittest.mock.patch(self.mock_send_request) as mock_send:
            mock_send.side_effect = requests.exceptions.RequestException("Network error")
            with self.assertRaises(requests.exceptions.RequestException):
                self.client.execute_query(self.shop_query_type, self.shop_query_name)

        with unittest.mock.patch(self.mock_send_request) as mock_send:
            mock_send.return_value = {"errors": ["API error"]}
            with self.assertRaises(ValueError):
                self.client.execute_query(self.shop_query_type, self.shop_query_name)

    @parameterized.expand(["store", "product"])
    def test_load_query_file(self, query_name) -> None:
        query_document = self.client_service._load_query_file(query_name)
        self.assertTrue(query_document)
        self.assertIsInstance(query_document, DocumentNode)
        self.assertTrue(query_document.definitions)

    def test_load_query(self) -> None:
        query_document = self.client_service._load_query_file(self.shop_query_type)
        query = self.client_service._get_query_and_fragments(query_document, self.shop_query_name)
        self.assertTrue(query)
        self.assertIsInstance(query, str)
        self.assertIn("query", query)
        self.assertIn(self.shop_query_name, query)
        self.assertIn("primaryDomain", query)

    @patch("pathlib.Path.read_text")
    def test_load_query_file_caching(self, mock_read_text) -> None:
        mock_read_text.return_value = "query { test }"

        self.client_service._load_query_file.cache_clear()
        result1 = self.client_service._load_query_file(self.shop_query_type)
        result2 = self.client_service._load_query_file(self.shop_query_type)

        mock_read_text.assert_called_once()
        self.assertEqual(result1, result2)
        self.client_service._load_query_file("product")
        self.assertEqual(mock_read_text.call_count, 2)

    def test_complex_query(self) -> None:
        variables = {"first": 5, "query": "title:Test*"}
        with unittest.mock.patch(self.mock_send_request) as mock_send:
            mock_send.return_value = {"data": {"products": {"edges": [{"node": {"title": "Test Product"}}]}}}
            result = self.client.execute_query("product", "GetProducts", variables, return_pydantic_model=False)

        self.assertIsInstance(result, list)
        self.assertTrue(all("title" in product for product in result))

    @unittest.mock.patch("time.time")
    def test_leak_bucket(self, mock_time) -> None:
        mock_time.return_value = 1000
        self.config.available_points = 0
        self.config.last_leak_time = 990
        self.client_service._leak_bucket()
        self.assertEqual(self.config.available_points, 1000)

    @unittest.mock.patch.object(time, "sleep")
    @unittest.mock.patch.object(time, "time")
    def test_wait_for_bucket(self, mock_time, mock_sleep) -> None:
        self.config.available_points = 0
        self.config.leak_rate = 10
        self.config.last_leak_time = 0
        self.config.max_bucket_size = 2000

        mock_time.side_effect = [i * 0.1 for i in range(200)]

        self.client_service._wait_for_bucket(100)
        mock_sleep.assert_called()

        total_sleep_time = sum(call.args[0] for call in mock_sleep.call_args_list)
        expected_sleep_time = 10
        self.assertAlmostEqual(total_sleep_time, expected_sleep_time, delta=0.5)

        for call in mock_sleep.call_args_list:
            self.assertLessEqual(call.args[0], 0.1)

        self.assertLessEqual(self.config.available_points, 10)


@tagged("post_install", "-at_install", "shopify")
class TestShopifyClientExternal(TestShopifyClientBaseExternal):

    def test_execute_query_shop(self) -> None:
        from odoo.addons.product_connect.services.models.shopify_shop import Shop

        shop = self.client.execute_query(self.shop_query_type, self.shop_query_name, pydantic_model=Shop)
        self.assertTrue(shop)
        self.assertTrue("opw-testing" in shop.name)
        self.assertTrue("opw-testing" in shop.primary_domain.host)

        _logger.info(shop)
        _logger.info(shop.name)

    def test_get_products(self) -> None:
        from odoo.addons.product_connect.services.models.shopify_product import Product

        location = self.client.get_first_location()
        query_type = "product"
        query_name = "GetProducts"
        variables = {
            "first": 5,
            "quantityNames": ["available"],
            "locationId": location,
        }
        products = self.client.execute_query(query_type, query_name, variables, pydantic_model=Product)
        self.assertTrue(products)
        self.assertTrue(len(products) > 0)
        self.assertTrue(products[0].title)
        self.assertIn("Test", products[0].title)

        _logger.info(products)
        _logger.info(products[0].title)
