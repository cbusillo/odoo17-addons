from logging.handlers import MemoryHandler

import logging

from odoo import api, models

logger = logging.getLogger(__name__)


class NotificationManagerMixin(models.AbstractModel):
    _name = "notification.manager.mixin"
    _description = "Notification Manager Mixin"

    ADMIN_EMAIL = "info@shinycomputers.com"

    def notify_channel(
        self,
        subject: str,
        body: str,
        channel_name: str,
        record: models.Model | None = None,
        env: api.Environment | None = None,
        logs: list[str] | None = None,
    ):
        env = env or self.env
        channel = env["discuss.channel"].search([("name", "=", channel_name)], limit=1)
        if not channel:
            channel = env["discuss.channel"].create({"name": channel_name})
        if logs:
            body += "\n\nRecent logs:\n"
            body += "\n".join(logs)

        logger.debug(
            "Sending message to channel %s with message %s for record %s",
            channel,
            body,
            record,
        )

        if record:
            record.message_post(body=body, subject=subject, message_type="auto_comment")
        else:
            channel.message_post(
                body=body, subject=subject, message_type="auto_comment"
            )

    def notify_channel_on_error(
        self,
        subject: str,
        body: str,
        record: models.Model | None = None,
        logs: list[str] | None = None,
    ):
        new_cr = self.env.registry.cursor()
        try:
            new_env = api.Environment(new_cr, self.env.uid, self.env.context)
            self.notify_channel(
                subject, body, "errors", record, new_env, logs
            )
            self.send_email_notification_to_admin(subject, body)
            new_cr.commit()
        finally:
            new_cr.close()

    def send_email_notification_to_admin(self, subject: str, body: str) -> None:
        recipient_partner = self.env["res.partner"].search(
            [("email", "=", self.ADMIN_EMAIL)], limit=1
        )
        if not recipient_partner:
            logger.error(
                "Recipient email %s not found among partners.", self.ADMIN_EMAIL
            )
            return

        # Create an email and send it
        mail_values = {
            "subject": subject,
            "body_html": f"<div>{body}</div>",
            "recipient_ids": [(4, recipient_partner.id)],
            "email_from": self.env["ir.mail_server"]
            .sudo()
            .search([], limit=1)
            .smtp_user,
        }
        mail = self.env["mail.mail"].sudo().create(mail_values)
        mail.send()
