import logging

from .models.shopify_product import Product

_logger = logging.getLogger(__name__)


class ShopifyParser:
    @staticmethod
    def extract_sku_bin_from_shopify_product(shopify_product: Product) -> tuple[str | None, str | None]:
        sku_field = shopify_product.variants[0].sku
        if not sku_field:
            _logger.warning(f"Shopify product {shopify_product.title}, ID: {shopify_product.id} has no SKU")
            return None, None

        sku_bin = [value.strip() if value else "" for value in sku_field.split(" - " if " - " in sku_field else " ", 1)]

        if len(sku_bin) == 0:
            _logger.warning(
                f"Unable to parse sku field ({sku_field}) for product {shopify_product.title}, ID: {shopify_product.id}"
            )
            return None, None

        sku = sku_bin[0]

        bin_location = sku_bin[1] if len(sku_bin) > 1 else ""
        return sku, bin_location

    @staticmethod
    def extract_id_from_gid(gid: str) -> int:
        return int(gid.split("/")[-1])

    @staticmethod
    def shopify_gid_from_id(resource_type: str, numeric_id: str) -> str:
        return f"gid://shopify/{resource_type}/{numeric_id}"

    @staticmethod
    def get_sku_bin(odoo_product: "odoo.model.product_template") -> str:
        return f"{odoo_product.default_code} - {odoo_product.bin}" if odoo_product.bin else odoo_product.default_code
