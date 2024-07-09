from odoo import api, fields, models


class ProductTemplate(models.Model):
    _name = "product.template"
    _inherit = ["product.base", "product.template"]
    _description = "Product"

    image_1920 = fields.Image(compute="_compute_image_1920", inverse="_inverse_image_1920", store=True)
    shopify_product_id = fields.Char(
        related="product_variant_ids.shopify_product_id",
        string="Shopify Product ID",
        readonly=True,
        store=True,
    )

    @api.depends("product_template_image_ids")
    def _compute_image_1920(self) -> None:
        for product in self:
            default_code = product.default_code  # Save the current default_code
            if product.product_template_image_ids:
                product.image_1920 = product.product_template_image_ids[0].image_1920
            else:
                product.image_1920 = False
            product.default_code = default_code

    def _inverse_image_1920(self) -> None:
        for product in self:
            if product.product_template_image_ids:
                product.product_template_image_ids[0].write({"image_1920": product.image_1920})

            elif product.image_1920:
                self.env["product.image"].create(
                    {
                        "product_tmpl_id": product.id,
                        "image_1920": product.image_1920,
                        "name": f"{product.name}_image",
                    }
                )
