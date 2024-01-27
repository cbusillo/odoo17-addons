from odoo import models, fields


class ProductProduct(models.Model):
    _inherit = "product.product"

    shopify_product_id = fields.Char(copy=False)
    shopify_variant_id = fields.Char(copy=False)
    shopify_condition_id = fields.Char(copy=False)
    shopify_last_exported = fields.Datetime(string="Last Exported Time")
    shopify_next_export = fields.Boolean(string="Export Next Sync?")
    shopify_created_at = fields.Datetime()

    def update_quantity(self, quantity):
        # noinspection PyUnresolvedReferences
        stock_location = self.env.ref("stock.stock_location_stock")
        for product in self:
            quant = self.env["stock.quant"].search(
                [("product_id", "=", product.id), ("location_id", "=", stock_location.id)], limit=1
            )

            if not quant:
                quant = self.env["stock.quant"].create({"product_id": product.id, "location_id": stock_location.id})

            quant.with_context(inventory_mode=True).write({"quantity": float(quantity)})
