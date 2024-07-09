import odoo
from odoo.exceptions import UserError


class ProductImportImage(odoo.models.Model):
    _name = "product.import.image"
    _inherit = ["image.mixin"]
    _description = "Product Import Image"
    _order = "index"
    # noinspection SqlResolve
    _sql_constraints = [
        ("index_uniq", "unique (index, product)", "Index must be unique per product!"),
    ]

    index = odoo.fields.Integer(index=True, required=True)
    product = odoo.fields.Many2one("product.import", ondelete="cascade", required=True, index=True)


class ProductImport(odoo.models.Model):
    _name = "product.import"
    _description = "Product Import"
    _inherit = ["product.base", "label.mixin"]

    images = odoo.fields.One2many("product.import.image", "product")
    condition = odoo.fields.Many2one(
        default=lambda self: self.env.ref("product_connect.product_condition_used", raise_if_not_found=False),
        required=True,
    )

    @odoo.api.onchange("default_code", "mpn", "condition", "bin", "qty_available")
    def _onchange_product_details(self) -> None:
        if self._origin.mpn != self.mpn or self._origin.condition != self.condition:
            existing_products = self.products_from_mpn_condition_new()
            if existing_products:
                existing_products_display = [
                    f"{product['default_code']} - {product['bin']}" for product in existing_products
                ]
                raise UserError(f"A product with the same MPN already exists.  Its SKU is {existing_products_display}")
