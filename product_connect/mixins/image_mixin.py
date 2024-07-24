from odoo import models, fields, api


class ImageMixin(models.AbstractModel):
    _description = "Image Mixin"
    _inherit = "image.mixin"

    file_size = fields.Integer(compute="_compute_file_size", store=True, group_operator="sum")

    @api.depends("image_1920")
    def _compute_file_size(self) -> None:
        for record in self:
            record.file_size = len(record.image_1920 or b'')

    def action_open_full_image(self) -> dict:
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/image?model=product.image&id=%s&field=image_1920' % self.id,
            'target': 'new',
        }
