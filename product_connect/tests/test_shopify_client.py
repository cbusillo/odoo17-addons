import logging
import time
import unittest
from unittest.mock import patch, mock_open

import requests
from graphql import DocumentNode
from odoo.tests import common, tagged, BaseCase
from parameterized import parameterized
from requests import Response, Session, PreparedRequest

from odoo.addons.product_connect.services.shopify_client import ShopifyClient

_logger = logging.getLogger(__name__)


class TestShopifyClientBase(common.HttpCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()

        shopify_client = cls.env["shopify.client"]
        shopify_client._overwrite_settings_from_dotenv()
        cls.client = shopify_client.create({})
        cls.shop_query_type = "store"
        cls.shop_query_name = "GetShop"

        cls.mock_send_request = "odoo.addons.product_connect.services.shopify_client.ShopifyClient._send_request"


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

    def test_settings(self) -> None:
        self.assertTrue(self.client.store_url_key)
        self.assertIn("myshopify.com", self.client.store_url)
        self.assertIn("shpat_", self.client.api_token)
        self.assertIn("-", self.client.api_version)
        self.assertIn("graphql.json", self.client.endpoint_url)
        self.assertTrue(self.client.endpoint_url.startswith("https://"))
        self.assertIn(self.client.store_url, self.client.endpoint_url)

    def test_get_client(self) -> None:
        self.assertTrue(self.client)

    def test_rate_limiting(self) -> None:
        with unittest.mock.patch(self.mock_send_request) as mock_send, unittest.mock.patch.object(
            self.client.__class__, "_wait_for_bucket"
        ) as mock_wait:
            mock_send.side_effect = [
                {
                    "data": {},
                    "extensions": {
                        "cost": {
                            "requestedQueryCost": 500,
                            "throttleStatus": {"currentlyAvailable": 1000, "restoreRate": 50, "maximumAvailable": 1000},
                        }
                    },
                },
                {
                    "data": {},
                    "extensions": {
                        "cost": {
                            "requestedQueryCost": 600,
                            "throttleStatus": {"currentlyAvailable": 400, "restoreRate": 50, "maximumAvailable": 1000},
                        }
                    },
                },
                {
                    "data": {},
                    "extensions": {
                        "cost": {
                            "requestedQueryCost": 500,
                            "throttleStatus": {"currentlyAvailable": 50, "restoreRate": 50, "maximumAvailable": 1000},
                        }
                    },
                },
            ]

            ShopifyClient._cls_session_available_points = 1000
            ShopifyClient._cls_session_max_bucket_size = 1000
            ShopifyClient._cls_session_leak_rate = 50

            self.client.execute_query(self.shop_query_type, self.shop_query_name, return_pydantic_model=False)
            self.client.execute_query(self.shop_query_type, self.shop_query_name, return_pydantic_model=False)
            self.client.execute_query(self.shop_query_type, self.shop_query_name, return_pydantic_model=False)

            # Assert that _wait_for_bucket was called at least once
            mock_wait.assert_called()

        # Assert the final available points
        self.assertEqual(ShopifyClient._cls_session_available_points, 50)

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
        query_document = self.client._load_query_file(query_name)
        self.assertTrue(query_document)
        self.assertIsInstance(query_document, DocumentNode)
        self.assertTrue(query_document.definitions)

    def test_load_query(self) -> None:
        query_document = self.client._load_query_file(self.shop_query_type)
        query = self.client._get_query_and_fragments(query_document, self.shop_query_name)
        self.assertTrue(query)
        self.assertIsInstance(query, str)
        self.assertIn("query", query)
        self.assertIn(self.shop_query_name, query)
        self.assertIn("primaryDomain", query)

    @patch(
        "odoo.addons.product_connect.services.shopify_client.open", new_callable=mock_open, read_data="query { test }"
    )
    def test_load_query_file_caching(self, mock_file) -> None:
        self.client._load_query_file(self.shop_query_type)
        self.client._load_query_file(self.shop_query_type)
        mock_file.assert_called_once()

        mock_file.assert_called_once_with(unittest.mock.ANY, "r")
        self.assertEqual(self.client._load_query_file("shop"), self.client._load_query_file("shop"))

    def test_complex_query(self) -> None:
        variables = {"first": 5, "query": "title:Test*"}
        with unittest.mock.patch(self.mock_send_request) as mock_send:
            mock_send.return_value = {"data": {"products": {"edges": [{"node": {"title": "Test Product"}}]}}}
            result = self.client.execute_query("product", "GetProducts", variables, return_pydantic_model=False)

        self.assertIsInstance(result, list)
        self.assertTrue(all("title" in product for product in result))

    def test_session_management(self) -> None:
        original_session = ShopifyClient._cls_session
        self.client.ensure_session()
        self.assertEqual(original_session, ShopifyClient._cls_session)

        ShopifyClient._cls_session = None
        self.client.ensure_session()
        self.assertIsNotNone(ShopifyClient._cls_session)
        self.assertNotEqual(original_session, ShopifyClient._cls_session)

    @unittest.mock.patch("time.time")
    def test_leak_bucket(self, mock_time) -> None:
        mock_time.return_value = 1000  # Set initial time
        ShopifyClient._cls_session_available_points = 0
        ShopifyClient._cls_session_last_leak_time = 990  # 10 seconds ago
        self.client._leak_bucket()
        self.assertEqual(ShopifyClient._cls_session_available_points, 1000)

    @unittest.mock.patch.object(time, "sleep")
    @unittest.mock.patch.object(time, "time")
    def test_wait_for_bucket(self, mock_time, mock_sleep) -> None:
        ShopifyClient._cls_session_available_points = 0
        ShopifyClient._cls_session_leak_rate = 10
        ShopifyClient._cls_session_last_leak_time = 0
        ShopifyClient._cls_session_max_bucket_size = 2000

        mock_time.side_effect = [i * 0.1 for i in range(200)]

        self.client._wait_for_bucket(100)
        mock_sleep.assert_called()

        total_sleep_time = sum(call.args[0] for call in mock_sleep.call_args_list)
        expected_sleep_time = 10
        self.assertAlmostEqual(total_sleep_time, expected_sleep_time, delta=0.5)

        for call in mock_sleep.call_args_list:
            self.assertLessEqual(call.args[0], 0.1)

        self.assertLessEqual(ShopifyClient._cls_session_available_points, 10)


@tagged("post_install", "-at_install", "shopify", "current")
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
