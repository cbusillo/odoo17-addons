from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"
    enable_custom_constraints = fields.Boolean(
        related="company_id.enable_custom_constraints",
        readonly=False,
    )
