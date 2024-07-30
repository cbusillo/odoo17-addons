import logging

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class ImageMixin(models.AbstractModel):
    _description = "Image Mixin"
    _inherit = "image.mixin"

    attachment = fields.Many2one("ir.attachment", compute="_compute_attachment", store=True)
    image_1920_file_size = fields.Integer(related="attachment.file_size", store=True)
    image_1920_file_size_kb = fields.Float(compute="_compute_image_1920_file_size_kb", string="Size in kB", store=True)
    index = fields.Integer()

    @api.depends("attachment")
    def _compute_attachment(self) -> None:
        IrAttachment = self.env["ir.attachment"]
        for image in self:
            image.attachment = IrAttachment.search(
                [
                    ("res_model", "=", self._name),
                    ("res_id", "=", image.id),
                    ("res_field", "=", "image_1920"),
                ],
                limit=1,
            )

    @api.depends("image_1920_file_size")
    def _compute_image_1920_file_size_kb(self) -> None:
        for image in self:
            image.image_1920_file_size_kb = round(image.image_1920_file_size / 1024, 2)

    def action_open_full_image(self) -> dict:
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "url": f"/web/image?model={self._name}&id={self.id}&field=image_1920",
            "target": "new",
        }
