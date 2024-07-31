from odoo import fields, models


class ProductProduct(models.Model):
    _inherit = "product.product"
    _description = "Product"

    shopify_product_id = fields.Char(copy=False)
    shopify_variant_id = fields.Char(copy=False)
    shopify_condition_id = fields.Char(copy=False)
    shopify_ebay_category_id = fields.Char(copy=False)
    shopify_last_exported = fields.Datetime(string="Last Exported Time")
    shopify_next_export = fields.Boolean(string="Export Next Sync?")
    shopify_created_at = fields.Datetime()

    def update_quantity(self, quantity: float) -> None:
        stock_location_ref = "stock.stock_location_stock"
        if not self.env.ref(stock_location_ref, raise_if_not_found=False):
            self.product_tmpl_id.notify_channel_on_error("Stock Location Not Found", stock_location_ref)
        stock_location = self.env.ref(stock_location_ref)
        if not stock_location.id:
            return

        for product in self:

            quant = self.env["stock.quant"].search(
                [
                    ("product_id", "=", product.id),
                    ("location_id", "=", stock_location.id),
                ],
                limit=1,
            )

            if not quant:
                quant = self.env["stock.quant"].create({"product_id": product.id, "location_id": stock_location.id})

            quant.with_context(inventory_mode=True).write({"quantity": float(quantity)})
