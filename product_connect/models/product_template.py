import re

from odoo.exceptions import ValidationError

from odoo import _, api, fields, models
from ..mixins.label import LabelMixin


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


class ProductTemplate(models.Model, LabelMixin):
    _inherit = "product.template"
    _description = "Product"
    _sql_constraints = [
        ("default_code_uniq", "unique(default_code)", "SKU must be unique."),
    ]

    length = fields.Integer()
    width = fields.Integer()
    height = fields.Integer()

    @api.constrains("length", "width", "height")
    def check_dimension_values(self) -> None:
        for record in self:
            fields_to_check = [record.length, record.width, record.height]
            for field_value in fields_to_check:
                if field_value and len(str(abs(field_value))) > 2:
                    raise ValidationError("Dimensions cannot exceed 2 digits.")

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
    default_code = fields.Char("SKU", index=True, default=lambda self: self.get_next_sku())
    image_1920 = fields.Image(compute="_compute_image_1920", inverse="_inverse_image_1920", store=True)

    shopify_product_id = fields.Char(
        related="product_variant_ids.shopify_product_id",
        string="Shopify Product ID",
        readonly=True,
        store=True,
    )

    def is_condition_valid(self, shopify_condition: str) -> bool:
        return shopify_condition in dict(self._fields["condition"].selection)

    def get_next_sku(self) -> str:
        sequence = self.env["ir.sequence"].search([("code", "=", "product.template.default_code")])
        padding = sequence.padding
        max_sku = "9" * padding
        while (new_sku := self.env["ir.sequence"].next_by_code("product.template.default_code")) <= max_sku:
            if not (self.env["motor.product"].search_count([("default_code", "=", new_sku)]) or
                    self.env["product.template"].search_count([("default_code", "=", new_sku)]) or
                    self.env["product.import"].search_count([("default_code", "=", new_sku)])):
                return new_sku
        raise ValidationError("SKU limit reached.")

    def _generate_next_sku(self) -> str:
        sequence = self.env["ir.sequence"].search([("code", "=", "product.import")])
        padding = sequence.padding
        max_sku = "9" * padding
        while (
                new_sku := self.env["ir.sequence"].next_by_code("product.import")
        ) <= max_sku:
            if not self.search([("default_code", "=", new_sku)]):
                return new_sku
        raise ValidationError("SKU limit reached.")

    @api.constrains("default_code")
    def _check_sku(self) -> None:
        for record in self:
            if not record.default_code:
                continue
            if not re.match(r"^\d{4,8}$", str(record.default_code)):
                raise ValidationError(_("SKU must be 4-8 digits."))

    @api.depends("product_template_image_ids")
    def _compute_image_1920(self) -> None:
        for record in self:
            default_code = record.default_code  # Save the current default_code
            if record.product_template_image_ids:
                record.image_1920 = record.product_template_image_ids[0].image_1920
            else:
                record.image_1920 = False
            record.default_code = default_code

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
