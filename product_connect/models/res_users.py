from odoo import fields, models


class Users(models.Model):
    _name = "res.users"
    _inherit = "res.users"

    is_technician = fields.Boolean(default=True)
