from odoo import models, fields


class Users(models.Model):
    _name = "res.users"
    _inherit = "res.users"

    is_technician = fields.Boolean(default=True)
