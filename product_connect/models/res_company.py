from odoo import fields, models


class Company(models.Model):
    _inherit = "res.company"
    enable_custom_constraints = fields.Boolean(default=False)
