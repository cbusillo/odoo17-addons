from odoo import fields, models


class MotorCylinder(models.Model):
    _name = "motor.cylinder"
    _description = "Motor Cylinder Data"
    _order = "cylinder_number"
    _sql_constraints = [
        (
            "motor_cylinder_number_unique",
            "unique(motor, cylinder_number)",
            "Cylinder number must be unique per motor.",
        )
    ]

    motor = fields.Many2one("motor", ondelete="restrict")
    cylinder_number = fields.Integer()
    compression_psi = fields.Integer("Compression PSI")


class MotorImage(models.Model):
    _name = "motor.image"
    _inherit = ["image.mixin"]
    _description = "Motor Images"

    motor = fields.Many2one("motor", ondelete="restrict")
    name = fields.Char()


class MotorStroke(models.Model):
    _name = "motor.stroke"
    _description = "Motor Stroke"
    _order = "sequence, id"

    name = fields.Char(required=True)
    code = fields.Char(required=True, index=True, readonly=True)
    sequence = fields.Integer(default=10)


class MotorConfiguration(models.Model):
    _name = "motor.configuration"
    _description = "Motor Configuration"
    _order = "sequence, id"

    name = fields.Char(required=True)
    code = fields.Char(required=True, index=True, readonly=True)
    sequence = fields.Integer(default=10)
