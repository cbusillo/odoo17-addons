import re
from typing import Any

from odoo import models, api, fields
from odoo.tools import float_round


def camel_to_snake(name: str) -> str:
    pattern = re.compile(r"(?<!^)(?=[A-Z])")
    return pattern.sub("_", name).lower()


def snake_to_camel(name: str) -> str:
    components = name.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


class ShopifyProduct(models.Model):
    _name = "shopify.product"
    _description = "Shopify Product"

    _location: int | None = None

    shopify_id = fields.Char(required=True, index=True)
    odoo_product = fields.Many2one("product.template", index=True)
    title = fields.Char(required=True)
    description = fields.Html()
    product_type = fields.Char()
    status = fields.Selection([("ACTIVE", "Active"), ("ARCHIVED", "Archived"), ("DRAFT", "Draft")], default="DRAFT")
    updated_at = fields.Datetime()
    created_at = fields.Datetime()
    vendor = fields.Char()
    handle = fields.Char(index=True)
    published_at = fields.Datetime()

    variant_id = fields.Char(index=True)
    sku = fields.Char()
    price = fields.Char()
    inventory_quantity = fields.Float()
    barcode = fields.Char()

    inventory_item_id = fields.Char(index=True)
    weight = fields.Float()

    inventory_level_id = fields.Char()
    location_id = fields.Char()
    location_name = fields.Char()

    last_sync_date = fields.Datetime()

    @api.model
    def create_or_update_from_shopify_data(self, shopify_data, sync_datetime: fields.Datetime):
        shopify_id = shopify_data["id"]
        existing_product = self.search([("shopify_id", "=", shopify_id)], limit=1)
        vals: "odoo.values.shopify_product" = {
            "shopify_id": shopify_id,
            "title": shopify_data["title"],
            "description": shopify_data["description"],
            "product_type": shopify_data["productType"],
            "status": shopify_data["status"],
            "updated_at": shopify_data["updatedAt"],
            "created_at": shopify_data["createdAt"],
            "vendor": shopify_data["vendor"],
            "handle": shopify_data["handle"],
            "published_at": shopify_data["publishedAt"],
            "last_sync_date": sync_datetime,
        }

        if variant := shopify_data.get("variants"):
            variant = variant[0]
            vals.update(
                {
                    "variant_id": variant["id"],
                    "sku": variant["sku"],
                    "price": variant["price"],
                    "inventory_quantity": variant["inventoryQuantity"],
                    "barcode": variant.get("barcode"),
                }
            )
            if inventory_item := variant.get("inventoryItem"):
                vals.update(
                    {
                        "inventory_item_id": inventory_item["id"],
                        "weight": inventory_item.get("weight", {}).get("value"),
                    }
                )

                if inventory_level := inventory_item.get("inventoryLevel"):
                    vals.update(
                        {
                            "inventory_level_id": inventory_level["id"],
                            "location_id": inventory_level.get("location", {}).get("id"),
                            "location_name": inventory_level.get("location", {}).get("name"),
                        }
                    )

        if existing_product:
            existing_product.write(vals)
            return existing_product
        else:
            return self.create(vals)

    def to_shopify_data(self) -> dict[str, Any]:
        data = {
            "title": self.title,
            "description": self.description,
            "productType": self.product_type,
            "status": self.status,
            "vendor": self.vendor,
            "handle": self.handle,
            "publishedAt": self.published_at,
        }

        if self.variant_id:
            data["variants"] = [
                {
                    "id": self.variant_id,
                    "sku": self.sku,
                    "price": self.price,
                    "inventoryQuantity": float_round(self.inventory_quantity, precision_digits=0),
                    "barcode": self.barcode,
                    "inventoryItem": {
                        "id": self.inventory_item_id,
                        "weight": {"value": self.weight},
                        "inventoryLevel": {
                            "id": self.inventory_level_id,
                            "location": {"id": self.location_id, "name": self.location_name},
                        },
                    },
                }
            ]

        data["images"] = [{"url": image.get_base_url()} for image in self.odoo_product.images]
        return data

    @api.model
    def sync_product_with_shopify(self, shopify_id: int | None) -> None:
        if not shopify_id:
            pass

        shopify_client = self.env["shopify.client"]()
        product_data = shopify_client.execute_query("product", "getProduct")
        print(product_data)
