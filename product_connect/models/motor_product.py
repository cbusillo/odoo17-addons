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
    qty_available = fields.Float()
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
    _inherit = ["product.base"]
    _description = "Motor Product"
    _order = "sequence, id"

    motor = fields.Many2one("motor", required=True, ondelete="restrict", readonly=True)
    images = fields.One2many("motor.product.image", "product")

    template = fields.Many2one("motor.product.template", required=True, ondelete="restrict", readonly=True)
    computed_name = fields.Char(compute="_compute_name", store=True)

    sequence = fields.Integer(related="template.sequence", index=True, store=True)
    excluded_parts = fields.Many2many("motor.part.template", related="template.excluded_parts")
    excluded_tests = fields.Many2many("motor.test.template", related="template.excluded_tests")

    is_listable = fields.Boolean(default=True)

    @api.depends("name", "computed_name", "default_code")
    def _compute_display_name(self) -> None:
        for product in self:
            product.display_name = f"{product.default_code} - {product.name or product.computed_name}"

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
        for product in self:
            name_parts = [
                product.motor.year if product.template.include_year_in_name else None,
                product.motor.manufacturer.name if product.motor.manufacturer else None,
                (product.motor.get_horsepower_formatted() if product.template.include_hp_in_name else None),
                product.template.name,
                product.first_mpn if product.template.include_model_in_name else None,
                "OEM" if product.template.include_oem_in_name else None,
            ]
            new_computed_name = " ".join(part for part in name_parts if part)
            if not product.name or product.name == product.computed_name:
                product.name = new_computed_name
            product.computed_name = new_computed_name

    def reset_name(self) -> None:
        for product in self:
            product.name = product.computed_name
