from odoo import api, fields, models
from ..utils import constants


class MotorProductTemplate(models.Model):
    _name = "motor.product.template"
    _description = "Motor Product Template"
    _order = "sequence, id"

    name = fields.Char(required=True)

    motor_stroke = fields.Selection(constants.MOTOR_STROKE_SELECTION)
    motor_configuration = fields.Selection(constants.MOTOR_CONFIGURATION_SELECTION)
    manufacturer = fields.Many2one("product.manufacturer", domain="[('is_engine_manufacturer', '=', True)]")
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
    sequence = fields.Integer(default=10)


class MotorProduct(models.Model):
    _name = "motor.product"
    _description = "Motor Product"
    _order = "sequence, id"

    motor = fields.Many2one("motor", required=True, ondelete="restrict")
    template = fields.Many2one("motor.product.template", required=True, ondelete="restrict")
    computed_name = fields.Char(compute="_compute_name", store=True)
    name = fields.Char()
    mpn = fields.Char()
    product_type = fields.Many2one(related="template.product_type", store=True)
    quantity = fields.Integer()
    bin = fields.Char()
    weight = fields.Float()
    price = fields.Float()
    sequence = fields.Integer(related="template.sequence", index=True, store=True)
    excluded_parts = fields.Many2many("motor.part.template", related="template.excluded_parts")
    excluded_tests = fields.Many2many("motor.test.template", related="template.excluded_tests")

    is_listable = fields.Boolean(default=True)

    @api.depends("motor.manufacturer.name", "template.name", "mpn")
    def _compute_name(self) -> None:
        for record in self:
            name_parts = [
                record.motor.year if record.template.include_year_in_name else None,
                record.motor.manufacturer.name,
                record.motor.get_horsepower_formatted() if record.template.include_hp_in_name else None,
                record.motor.model if record.template.include_model_in_name else None,
                record.template.name,
                record.mpn if record.template.include_model_in_name else None,
                "OEM" if record.template.include_oem_in_name else None,
            ]
            record.computed_name = " ".join(part for part in name_parts if part)
