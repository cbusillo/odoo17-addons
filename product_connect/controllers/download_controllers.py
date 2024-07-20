import base64

from odoo import http
from odoo.http import request, Response, NotFound


class SingleDownloadController(http.Controller):
    @http.route("/web/binary/download_single", type="http", auth="user")
    def download_single(self, attachment_id: str, **_kwargs: str) -> Response | NotFound:
        attachment = request.env["ir.attachment"].sudo().browse(int(attachment_id))
        if not attachment:
            return request.not_found()

        file_content = base64.b64decode(attachment.datas)
        filename = attachment.name
        content_type = attachment.mimetype or "application/octet-stream"

        attachment.sudo().unlink()

        return request.make_response(
            file_content,
            [
                ("Content-Type", content_type),
                ("Content-Disposition", f'attachment; filename="{filename}"'),
                ("Content-Length", len(file_content)),
            ],
        )
