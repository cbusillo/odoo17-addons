import re

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from ..mixins.product_labels import ProductLabelsMixin


class ProductType(models.Model):
    _name = "product.type"
    _description = "Product Type"
    _sql_constraints = [
        ("name_uniq", "unique (name)", "Product Type name already exists !"),
    ]

    name = fields.Char(required=True, index=True)
    ebay_category_id = fields.Integer(string="eBay Category ID", index=True)
    product_count = fields.Integer(
        string="Number of Products", compute="_compute_product_count", store=True
    )

    @api.depends("product_ids")
    def _compute_product_count(self) -> None:
        for record in self:
            record.product_count = len(record.product_ids)

    product_ids = fields.One2many("product.template", "part_type", string="Products")


class ProductTemplate(models.Model, ProductLabelsMixin):
    _inherit = "product.template"

    bin = fields.Char(index=True)
    mpn = fields.Char(string="MPN", index=True)
    lot_number = fields.Char(index=True)
    manufacturer = fields.Many2one("product.manufacturer", index=True)
    manufacturer_barcode = fields.Char(index=True)
    part_type = fields.Many2one("product.type", index=True)
    condition = fields.Selection(
        [
            ("used", "Used"),
            ("new", "New"),
            ("open_box", "Open Box"),
            ("broken", "Broken"),
            ("refurbished", "Refurbished"),
        ],
        default="used",
    )
    default_code = fields.Char("SKU", index=True, required=False)
    image_1920 = fields.Image(
        compute="_compute_image_1920", inverse="_inverse_image_1920", store=True
    )

    shopify_product_id = fields.Char(
        related="product_variant_ids.shopify_product_id",
        string="Shopify Product ID",
        readonly=True,
        store=True,
    )

    def is_condition_valid(self, shopify_condition) -> bool:
        return shopify_condition in dict(self._fields["condition"].selection)

    @api.constrains("default_code")
    def _check_default_code(self) -> None:
        for record in self:
            if not re.match(r"^\d{4,8}$", str(record.default_code)):
                raise ValidationError(_("SKU must be 4-8 digits."))

            duplicate_count = self.search_count(
                [("default_code", "=", record.default_code), ("id", "!=", record.id)]
            )
            if duplicate_count > 0:
                raise ValidationError(_("SKU must be unique."))

    @api.depends("product_template_image_ids")
    def _compute_image_1920(self) -> None:
        for record in self:
            if record.product_template_image_ids:
                record.image_1920 = record.product_template_image_ids[0].image_1920
            else:
                record.image_1920 = False

    def _inverse_image_1920(self) -> None:
        for record in self:
            if record.product_template_image_ids:
                record.product_template_image_ids[0].write(
                    {"image_1920": record.image_1920}
                )

            elif record.image_1920:
                self.env["product.image"].create(
                    {
                        "product_tmpl_id": record.id,
                        "image_1920": record.image_1920,
                        "name": f"{record.name}_image",
                    }
                )
