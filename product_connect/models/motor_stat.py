from odoo import fields, models


class MotorCompression(models.Model):
    _name = "motor.compression"
    _description = "Motor Compression Data"
    _order = "cylinder_number"

    motor = fields.Many2one("motor", ondelete="restrict")
    cylinder_number = fields.Integer()
    compression_psi = fields.Integer("Compression PSI")
    compression_image = fields.Binary()


class MotorImage(models.Model):
    _name = "motor.image"
    _inherit = ["image.mixin"]
    _description = "Motor Images"

    motor = fields.Many2one("motor", ondelete="restrict")
    name = fields.Char()
    image_data = fields.Binary()


class MotorStroke(models.Model):
    _name = "motor.stroke"
    _description = "Motor Stroke"
    _order = "sequence, id"

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    sequence = fields.Integer(default=10)


class MotorConfiguration(models.Model):
    _name = "motor.configuration"
    _description = "Motor Configuration"
    _order = "sequence, id"

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    sequence = fields.Integer(default=10)
