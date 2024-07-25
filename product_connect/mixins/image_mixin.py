from odoo import models, fields, api


class ImageMixin(models.AbstractModel):
    _description = "Image Mixin"
    _inherit = "image.mixin"

    attachment = fields.Many2one(
        "ir.attachment", compute="_compute_attachment", store=True
    )
    image_1920_file_size = fields.Integer(related="attachment.file_size", store=True)

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

    def action_open_full_image(self) -> dict:
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "url": f"/web/image?model={self._name}&id=%s&field=image_1920{self.id}",
            "target": "new",
        }
