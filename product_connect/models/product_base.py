import re

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ProductBase(models.AbstractModel):
    _name = "product.base"
    _inherit = ["label.mixin"]
    _description = "Product Base"
    _order = "create_date desc"
    _sql_constraints = [
        ("default_code_uniq", "unique(default_code)", "SKU must be unique."),
    ]

    name = fields.Char(required=True, index=True)
    default_code = fields.Char("SKU", index=True, copy=False, default=lambda self: self.get_next_sku())
    create_date = fields.Datetime(index=True)

    mpn = fields.Char(string="MPN", index=True)
    manufacturer = fields.Many2one("product.manufacturer", index=True)
    part_type = fields.Many2one("product.type", index=True)
    condition = fields.Many2one("product.condition", index=True)

    length = fields.Integer()
    width = fields.Integer()
    height = fields.Integer()
    weight = fields.Float()

    bin = fields.Char(index=True)
    quantity = fields.Integer()

    list_price = fields.Float(string="Sale Price")
    standard_price = fields.Float(string="Cost")

    description = fields.Text()

    active = fields.Boolean(default=True)

    @api.constrains("default_code")
    def _check_sku(self) -> None:
        for record in self:
            if not record.default_code:
                continue
            if not re.match(r"^\d{4,8}$", str(record.default_code)):
                raise ValidationError(_("SKU must be 4-8 digits."))

    def get_next_sku(self) -> str:
        sequence = self.env["ir.sequence"].search([("code", "=", "product.template.default_code")])
        padding = sequence.padding
        max_sku = "9" * padding
        while (new_sku := self.env["ir.sequence"].next_by_code("product.template.default_code")) <= max_sku:
            if not (
                self.env["motor.product"].search_count([("default_code", "=", new_sku)])
                or self.env["product.template"].search_count([("default_code", "=", new_sku)])
                or self.env["product.import"].search_count([("default_code", "=", new_sku)])
            ):
                return new_sku
        raise ValidationError("SKU limit reached.")

    @api.constrains("length", "width", "height")
    def check_dimension_values(self) -> None:
        for record in self:
            fields_to_check = [record.length, record.width, record.height]
            for field_value in fields_to_check:
                if field_value and len(str(abs(field_value))) > 2:
                    raise ValidationError("Dimensions cannot exceed 2 digits.")
