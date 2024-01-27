from datetime import datetime, timedelta, timezone

from odoo import models, fields, api


class ShopifyZeroSalesWizardLine(models.TransientModel):
    _name = "shopify.zero.sales.wizard.line"
    _description = "Shopify Zero Sales Wizard Line"

    wizard_id = fields.Many2one("shopify.zero.sales.wizard", string="Wizard")
    product_template_id = fields.Many2one("product.template", string="Product")
    shopify_product_id = fields.Char(related="product_template_id.shopify_product_id", string="Shopify Product ID", store=True)
    product_quantity = fields.Float(related="product_template_id.qty_available", string="Quantity", store=True)
    product_created_at = fields.Datetime()
    product_age = fields.Char(compute="_compute_product_age")
    product_price = fields.Float(string="Price", store=True)

    @api.onchange("product_price")
    def _onchange_product_price(self):
        if self.product_template_id.list_price != self.product_price:
            self.product_template_id.list_price = self.product_price

    @api.depends("product_created_at")
    def _compute_product_age(self):
        for record in self:
            if record.product_created_at:
                product_created_at_aware = (
                    record.product_created_at.replace(tzinfo=timezone.utc)
                    if record.product_created_at.tzinfo is None
                    else record.product_created_at
                )
                delta = (datetime.now(timezone.utc) - product_created_at_aware).days
                record.product_age = f"{delta} days"

    def open_product(self):
        self.ensure_one()
        product = self.env["product.template"].search([("shopify_product_id", "=", self.shopify_product_id)], limit=1)
        return {
            "name": "Product",
            "type": "ir.actions.act_window",
            "res_model": "product.template",
            "res_id": product.id,
            "view_mode": "form",
            "target": "current",
        }


class ShopifyZeroSalesWizard(models.TransientModel):
    _name = "shopify.zero.sales.wizard"
    _description = "Shopify Zero Sales Wizard"
    DEFAULT_TIME_DELTA = timedelta(days=30)

    date_filter = fields.Datetime(required=True, default=lambda self: fields.Datetime.now(timezone.utc) - self.DEFAULT_TIME_DELTA)
    line_ids = fields.One2many("shopify.zero.sales.wizard.line", "wizard_id", string="Lines")

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        res["line_ids"] = self.get_zero_sales()
        return res

    @api.onchange("date_filter")
    def onchange_date_filter(self):
        self.line_ids = [(5, 0, 0)] + self.get_zero_sales()

    @api.model
    def get_zero_sales(self):
        if self.date_filter:
            date_filter = self.date_filter.replace(tzinfo=timezone.utc)
        else:
            date_filter = datetime.now(timezone.utc) - self.DEFAULT_TIME_DELTA
        product_ids = self.env["shopify.sync"].get_products_with_no_sales(date_filter)
        products = self.env["product.template"].search([("shopify_product_id", "in", product_ids)])

        lines = []
        for product in products:
            earliest_write_date = min(
                filter(
                    None,
                    [
                        product.product_variant_id.write_date,
                        product.write_date,
                        product.product_variant_id.shopify_created_at,
                    ],
                )
            )
            line_values = {
                "product_template_id": product.id,
                "product_created_at": earliest_write_date,
                "product_price": product.list_price,
            }
            lines.append((0, 0, line_values))
        return lines
