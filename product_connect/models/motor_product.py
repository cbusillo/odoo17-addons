from typing import Any, Self

from odoo import api, fields, models


class MotorProductTemplate(models.Model):
    _name = "motor.product.template"
    _description = "Motor Product Template"
    _order = "sequence, id"

    name = fields.Char(required=True)

    stroke = fields.Many2many("motor.stroke")
    configuration = fields.Many2many("motor.configuration")
    manufacturers = fields.Many2many("product.manufacturer", domain=[("is_motor_manufacturer", "=", True)])
    excluded_parts = fields.Many2many("motor.part.template")
    excluded_tests = fields.Many2many("motor.test.template")
    is_quantity_listing = fields.Boolean(default=False)
    include_year_in_name = fields.Boolean(default=True)
    include_hp_in_name = fields.Boolean(default=True)
    include_model_in_name = fields.Boolean(default=True)
    include_oem_in_name = fields.Boolean(default=True)

    product_type = fields.Many2one("product.type", index=True)
    quantity = fields.Integer()
    bin = fields.Char()
    weight = fields.Float()
    sequence = fields.Integer(default=10, index=True)


class MotorProductImage(models.Model):
    _name = "motor.product.image"
    _inherit = ["image.mixin"]
    _description = "Motor Product Images"

    index = fields.Integer(index=True, required=True)
    product = fields.Many2one("motor.product", ondelete="restrict")


class MotorProduct(models.Model):
    _name = "motor.product"
    _description = "Motor Product"
    _order = "sequence, id"

    default_code = fields.Char(
        required=True,
        index=True,
        copy=False,
        readonly=True,
        default=lambda self: self.env["product.template"].get_next_sku(),
        string="SKU",
    )
    motor = fields.Many2one("motor", required=True, ondelete="restrict", readonly=True)
    active = fields.Boolean(default=True)
    images = fields.One2many("motor.product.image", "product")
    image_count = fields.Integer(compute="_compute_image_count")
    icon = fields.Binary(compute="_compute_icon", store=True)
    template = fields.Many2one("motor.product.template", required=True, ondelete="restrict", readonly=True)
    computed_name = fields.Char(compute="_compute_name", store=True)
    name = fields.Char()
    description = fields.Text()
    mpn = fields.Char()
    product_type = fields.Many2one(related="template.product_type", store=True)
    quantity = fields.Integer()
    bin = fields.Char()
    weight = fields.Float()
    price = fields.Float()
    cost = fields.Float()
    sequence = fields.Integer(related="template.sequence", index=True, store=True)
    excluded_parts = fields.Many2many("motor.part.template", related="template.excluded_parts")
    excluded_tests = fields.Many2many("motor.test.template", related="template.excluded_tests")

    is_listable = fields.Boolean(default=True)

    @api.model_create_multi
    def create(self, vals_list: list[dict[str, Any]]) -> Self:
        for vals in vals_list:
            vals["default_code"] = self.env["product.template"].get_next_sku()
        return super().create(vals_list)

    def _compute_image_count(self) -> None:
        for product in self:
            product.image_count = len([image for image in product.images if image.image_1920])

    @api.depends("name", "computed_name", "default_code")
    def _compute_display_name(self) -> None:
        for record in self:
            record.display_name = f"{record.default_code} - {record.name or record.computed_name}"

    @api.depends("images.image_1920")
    def _compute_icon(self) -> None:
        for record in self:
            record.icon = record.images[0].image_128 if record.images else None

    @api.depends(
        "motor.manufacturer.name",
        "template.name",
        "mpn",
        "motor.year",
        "motor.horsepower",
        "template.include_year_in_name",
        "template.include_hp_in_name",
        "template.include_model_in_name",
        "template.include_oem_in_name",
    )
    def _compute_name(self) -> None:
        for record in self:
            name_parts = [
                record.motor.year if record.template.include_year_in_name else None,
                record.motor.manufacturer.name if record.motor.manufacturer else None,
                (record.motor.get_horsepower_formatted() if record.template.include_hp_in_name else None),
                record.template.name,
                record.mpn if record.template.include_model_in_name else None,
                "OEM" if record.template.include_oem_in_name else None,
            ]
            new_computed_name = " ".join(part for part in name_parts if part)
            if not record.name or record.name == record.computed_name:
                record.name = new_computed_name
            record.computed_name = new_computed_name

    def reset_name(self) -> None:
        for record in self:
            record.name = record.computed_name
