import logging
import time
import unittest

import requests
from graphql import DocumentNode
from odoo.tests import common, tagged, BaseCase
from parameterized import parameterized
from requests import Response, Session, PreparedRequest

_logger = logging.getLogger(__name__)


class TestShopifyClientBase(common.HttpCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()

        cls.ShopifyClient = cls.env["shopify.client"]
        cls.ShopifyClient._overwrite_settings_from_dotenv()
        cls.client = cls.ShopifyClient.create({})
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

    @parameterized.expand(["shop", "product"])
    def test_load_query(self, query_type: str) -> None:
        document = self.env["shopify.client"]._load_query_file(query_type)
        self.assertTrue(document)
        self.assertIsInstance(document, DocumentNode)

    def test_get_client(self) -> None:
        self.assertTrue(self.client)

    def test_rate_limiting(self) -> None:
        with unittest.mock.patch(self.mock_send_request) as mock_send, unittest.mock.patch.object(
            self.ShopifyClient, "_wait_for_bucket"
        ) as mock_wait:
            mock_send.side_effect = [
                {"extensions": {"cost": {"throttleStatus": {"currentlyAvailable": 10, "restoreRate": 50}}}},
                {"extensions": {"cost": {"throttleStatus": {"currentlyAvailable": 0, "restoreRate": 50}}}},
                {"extensions": {"cost": {"throttleStatus": {"currentlyAvailable": 50, "restoreRate": 50}}}},
            ]

            self.client.execute_query(self.shop_query_type, self.shop_query_name, return_pydantic_model=False)
            self.client.execute_query(self.shop_query_type, self.shop_query_name)
            self.client.execute_query(self.shop_query_type, self.shop_query_name)

            mock_wait.assert_called()

    def test_error_handling(self) -> None:
        with unittest.mock.patch(self.mock_send_request) as mock_send:
            mock_send.side_effect = requests.exceptions.RequestException("Network error")
            with self.assertRaises(requests.exceptions.RequestException):
                self.client.execute_query(self.shop_query_type, self.shop_query_name)

        with unittest.mock.patch(self.mock_send_request) as mock_send:
            mock_send.return_value = {"errors": ["API error"]}
            with self.assertRaises(ValueError):
                self.client.execute_query(self.shop_query_type, self.shop_query_name)

    def test_caching(self) -> None:
        with unittest.mock.patch("builtins.open", unittest.mock.mock_open(read_data="query { test }")) as mock_file:
            self.client._load_query_file(self.shop_query_type)
            self.client._load_query_file(self.shop_query_type)
            mock_file.assert_called_once()

    def test_complex_query(self) -> None:
        variables = {"first": 5, "query": "title:Test*"}
        with unittest.mock.patch(self.mock_send_request) as mock_send:
            mock_send.return_value = {"data": {"products": {"edges": [{"node": {"title": "Test Product"}}]}}}
            result = self.client.execute_query("product", "getProducts", variables)

        self.assertIsInstance(result, list)
        self.assertTrue(all("title" in product for product in result))

    def test_session_management(self) -> None:
        original_session = self.client._session
        self.client.ensure_session()
        self.assertEqual(original_session, self.client._session)

        self.ShopifyClient._session = None
        self.client.ensure_session()
        self.assertIsNotNone(self.client._session)
        self.assertNotEqual(original_session, self.client._session)

    @unittest.mock.patch("time.time")
    def test_leak_bucket(self, mock_time) -> None:
        mock_time.return_value = 1000  # Set initial time
        self.ShopifyClient._session_available_points = 0
        self.ShopifyClient._session_last_leak_time = 990  # 10 seconds ago
        self.client._leak_bucket()
        self.assertEqual(self.client._session_available_points, 1000)  # 10 seconds * 100 points/second

    @unittest.mock.patch.object(time, "sleep")
    def test_wait_for_bucket(self, mock_sleep) -> None:
        self.ShopifyClient._session_available_points = 0
        self.ShopifyClient._session_leak_rate = 10
        self.client._wait_for_bucket(100)

        expected_sleep_time = 10
        mock_sleep.assert_called_with(expected_sleep_time)


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

        _logger.info(products)
        _logger.info(products[0].title)
