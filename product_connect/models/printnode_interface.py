import base64
import datetime
import logging

from printnodeapi import Gateway
from printnodeapi.model import Printer
from simple_zpl2 import ZPLDocument
from odoo import models, api, fields, _
from odoo.exceptions import UserError

logger = logging.getLogger(__name__)


class PrintNodeInterface(models.Model):
    _name = "printnode.interface"
    _description = "PrintNode Interface"
    _sql_constraints = [
        (
            "user_id_print_job_type_unique",
            "unique(user_id, print_job_type)",
            "Printer already selected for this job type and user",
        )
    ]

    printer_selection = fields.Selection(
        selection="get_printer_tuple", string="Printer"
    )
    print_job_type = fields.Selection(
        selection=[
            ("product_import_label", "Product Import Label"),
            ("receipt", "Receipt"),
        ],
        default="product_import_label",
    )
    user_id = fields.Many2one("res.users", default=lambda self: self.env.user)

    LABEL_SIZE = {"width": 2.2, "height": 1.3}
    LABEL_TEXT_SIZE = {"large": 60, "medium": 35, "small": 20}
    LABEL_PADDING_Y = 10
    LABEL_PADDING_X = 10
    LABEL_CENTER_X = 220
    LABEL_BOTTOM_TEXT_Y = 210
    BARCODE_SIZE = 8

    def get_gateway(self) -> Gateway:
        api_key = self.env["ir.config_parameter"].sudo().get_param("printnode.api_key")
        if not api_key:
            raise UserError(_("No PrintNode API key found"))
        return Gateway(apikey=api_key)

    def get_printers(self) -> list[Printer]:
        gateway = self.get_gateway()
        printers = gateway.printers()
        if not printers:
            raise UserError(_("No printers found on PrintNode"))
        return printers

    def get_printer_tuple(self) -> list[tuple[int, str]]:
        printers = self.get_printers()
        return [(printer.id, printer.name) for printer in printers]

    @api.model
    def print_label(self, label: base64, quantity: int = 1):
        gateway = self.get_gateway()
        user = self.env["printnode.interface"].search(
            [("user_id", "=", self.env.user.id)], limit=1
        )
        if not user:
            return False
        printer = user.printer_selection
        if not printer:
            return False
        print_job = None
        try:
            print_job = gateway.PrintJob(
                printer=int(printer),
                job_type="raw",
                title="Odoo Product Label",
                options={"copies": quantity},
                base64=label,
            )
        except LookupError as error:
            logger.exception(f"Error printing label: {error}")
        finally:
            return print_job

    def generate_label(
        self,
        text: list[str] | str,
        bottom_text: str | list[str] | None = None,
        barcode: str | None = None,
        quantity: int = 1,
        print_date: bool = True,
    ) -> base64:
        if not isinstance(text, list):
            text = [text]

        if bottom_text and not isinstance(bottom_text, list):
            bottom_text = [bottom_text]

        label_width = int(203 * self.LABEL_SIZE["width"])
        column_width = int(label_width / 2)
        label_text_size = (
            self.LABEL_TEXT_SIZE["large"]
            if text[0] == ""
            else self.LABEL_TEXT_SIZE["medium"]
        )

        quantity = max(int(quantity), 1)
        label = ZPLDocument()
        label.add_zpl_raw("^BY2")

        current_origin_y = self.LABEL_PADDING_Y

        if print_date:
            today = datetime.date.today()
            formatted_date = f"{today.month}.{today.day}.{today.year}"
            label.add_default_font(
                font_name=0,
                character_height=self.LABEL_TEXT_SIZE["small"],
                character_width=self.LABEL_TEXT_SIZE["small"],
            )
            label.add_field_block(text_justification="C", width=column_width)
            label.add_field_origin(
                x_pos=self.LABEL_CENTER_X, y_pos=current_origin_y, justification=2
            )
            label.add_field_data(formatted_date)
            current_origin_y += self.LABEL_TEXT_SIZE["small"]

        for line in text:
            current_line_text_size = (
                self.LABEL_TEXT_SIZE["small"]
                if line.startswith("(SM)") and len(line.replace("(SM)", "")) > 8
                else label_text_size
            )
            line = line.replace("(SM)", "")
            label.add_default_font(
                font_name=0,
                character_height=current_line_text_size,
                character_width=current_line_text_size,
            )
            label.add_field_block(text_justification="C", width=column_width)
            label.add_field_origin(
                x_pos=self.LABEL_CENTER_X, y_pos=current_origin_y, justification=2
            )
            label.add_field_data(line)
            current_origin_y += label_text_size

        if bottom_text:
            current_origin_y = self.LABEL_BOTTOM_TEXT_Y
            for line in bottom_text:
                label.add_default_font(
                    font_name=0,
                    character_height=self.LABEL_TEXT_SIZE["small"],
                    character_width=self.LABEL_TEXT_SIZE["small"],
                )
                label.add_field_block(text_justification="C", width=label_width)
                label.add_field_origin(y_pos=current_origin_y, justification=2)
                label.add_field_data(line)
                current_origin_y += self.LABEL_TEXT_SIZE["small"]

        if barcode:
            label.add_field_origin(
                x_pos=self.LABEL_PADDING_X, y_pos=self.LABEL_PADDING_Y, justification=2
            )
            # noinspection SpellCheckingInspection
            label.add_zpl_raw(f"^BQN,2,{self.BARCODE_SIZE}^FDQAH," + barcode + "^FS^XZ")

        zpl_text_with_quantity = label.zpl_text * quantity

        return base64.b64encode(zpl_text_with_quantity.encode("utf-8")).decode()

    @staticmethod
    def combine_labels(labels: list[str]) -> str:
        decoded_labels = [base64.b64decode(label).decode() for label in labels]
        combined_labels = "".join(decoded_labels)
        combined_labels_base64 = base64.b64encode(combined_labels.encode()).decode()
        return combined_labels_base64
