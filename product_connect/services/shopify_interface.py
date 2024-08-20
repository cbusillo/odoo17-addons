import logging
from datetime import datetime
from typing import Any, Generator
from zoneinfo import ZoneInfo

from dateutil.parser import parse
from odoo import models, fields, api

from .models.shopify_product import Product as ShopifyProduct
from .shopify_client import ShopifyClientService
from .shopify_parser import ShopifyParser

_logger = logging.getLogger(__name__)

UTC = ZoneInfo("UTC")


def parse_to_utc(date_str: str) -> datetime:
    return parse(date_str).astimezone(UTC)


def current_utc_time() -> datetime:
    return datetime.now(UTC)


class ShopifyInterface(models.AbstractModel):
    _name = "shopify.interface"
    _description = "Shopify Interface"

    from_dot_env = fields.Boolean(default=False)  # TODO: change from_dot_env to False in production

    def get_first_location(self) -> str:
        from odoo.addons.product_connect.services.models.shopify_product import Location

        client = self.init_client()
        location = client.execute_query_without_pagination("store", "GetLocation", pydantic_model=Location)
        return location.id

    @property
    def endpoint_url(self) -> str:
        client = ShopifyClientService(self.env, self.from_dot_env)
        return client.endpoint_url

    def fetch_import_timestamps(self) -> tuple[str, datetime, datetime]:
        last_import_time_str = str(self.env["ir.config_parameter"].sudo().get_param("shopify.last_import_time"))
        current_import_start_time = current_utc_time()
        last_import_time = parse_to_utc(last_import_time_str)
        return last_import_time_str, current_import_start_time, last_import_time

    @api.model
    def init_client(self) -> ShopifyClientService:
        return ShopifyClientService(self.env, self.from_dot_env)

    @api.model
    def fetch_shopify_products(self, last_sync_time_str: str | None = None) -> Generator[ShopifyProduct, None, None]:
        client = self.init_client()
        query_type = "product"
        query_name = "GetProducts"
        variables = {"query": f"updated_at:>{last_sync_time_str}" if last_sync_time_str else None}

        return client.execute_query(
            query_type,
            query_name,
            variables,
            pydantic_model=ShopifyProduct,
        )

    @api.model
    def update_or_create_odoo_product(self, shopify_product: ShopifyProduct) -> models.Model | None:
        OdooProduct = self.env["product.product"]

        sku, bin_location = ShopifyParser.extract_sku_bin_from_shopify_product(shopify_product)
        if not sku:
            _logger.warning(f"Unable to parse SKU for product {shopify_product.title}, ID: {shopify_product.id}")
            return None

        odoo_product = OdooProduct.search(
            [("shopify_product_id", "=", ShopifyParser.extract_id_from_gid(shopify_product.id))],
            limit=1,
        )

        if not odoo_product:
            odoo_product = OdooProduct.search([("default_code", "=", sku)], limit=1)

        shopify_product_data = self._prepare_odoo_product_data(shopify_product, sku, bin_location)

        if odoo_product:
            odoo_product.write(shopify_product_data)
            return odoo_product
        else:
            return OdooProduct.create(shopify_product_data)

    @staticmethod  # TODO: finish fields
    def _prepare_odoo_product_data(shopify_product: ShopifyProduct, sku: str, bin_location: str) -> dict:
        return {
            "shopify_product_id": ShopifyParser.extract_id_from_gid(shopify_product.id),
            "name": shopify_product.title,
            "default_code": sku,
            "type": "product",
            "list_price": shopify_product.variants[0].price,
            "bin": bin_location,
        }

    def sync_products_from_shopify(self) -> None:
        last_import_time_str, current_import_start_time, last_import_time = self.fetch_import_timestamps()

        shopify_products = self.fetch_shopify_products(last_import_time_str)

        updated_count = 0
        skipped_count = 0

        for shopify_product in shopify_products:
            result = self.update_or_create_odoo_product(shopify_product)
            if result:
                updated_count += 1
            else:
                skipped_count += 1

        self.env["ir.config_parameter"].sudo().set_param(
            "shopify.last_import_time",
            current_import_start_time.isoformat(timespec="seconds").replace("+00:00", "Z"),
        )
        _logger.info(
            f"Shopify products sync completed. Updated: {updated_count}, Skipped: {skipped_count}, "
            f"Start import time: {current_import_start_time}"
        )

    @staticmethod  # TODO: finish fields (variant id)
    def _prepare_shopify_product_data(odoo_product: "odoo.model.product_product") -> dict[str, Any]:
        if not odoo_product.default_code:
            _logger.warning(f"Skipping product {odoo_product.name} as it has no SKU")
            return {}

        sku_bin_field = ShopifyParser.get_sku_bin(odoo_product)

        return {
            "title": odoo_product.name,
            "description": odoo_product.description,
            "productType": odoo_product.type,
        }

    @api.model
    def sync_products_to_shopify(self) -> None:
        Product = self.env["product.product"]
        products_to_sync = Product.search(
            [
                "|",
                ("shopify_product_id", "=", False),
                ("write_date", ">", fields.Datetime.to_string(Product.shopify_last_exported)),
            ]
        )

        updated_count = 0
        skipped_count = 0
        for product in products_to_sync:
            product_data = self._prepare_shopify_product_data(product)
            if not product_data:
                skipped_count += 1
                continue

            if product.shopify_product_id:
                self.update_shopify_product(product)
            else:
                self.create_shopify_product(product)
            updated_count += 1

        _logger.info(f"Sync to Shopify completed. Updated: {updated_count}, Skipped: {skipped_count}")

    @api.model
    def create_shopify_product(self, odoo_product: "odoo.model.product_product") -> ShopifyProduct:
        client = self.init_client()
        product_data = self._prepare_shopify_product_data(odoo_product)

        result = client.execute_query_without_pagination(
            "product",
            "CreateProduct",
            {"input": product_data},
            pydantic_model=ShopifyProduct,
        )

        odoo_product.write({"shopify_product_id": result.id, "shopify_last_exported": current_utc_time()})

        return result

    @api.model
    def update_shopify_product(self, odoo_product: "odoo.model.product_product") -> ShopifyProduct:
        client = self.init_client()
        product_data = self._prepare_shopify_product_data(odoo_product)
        product_data["id"] = ShopifyParser.shopify_gid_from_id("product", odoo_product.shopify_product_id)

        result = client.execute_query_without_pagination(
            "product",
            "UpdateProduct",
            {"input": product_data},
            pydantic_model=ShopifyProduct,
        )

        odoo_product.shopify_last_exported = current_utc_time()

        return result
