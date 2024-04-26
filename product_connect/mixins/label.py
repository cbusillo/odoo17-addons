import base64
import datetime
import logging
from typing import TYPE_CHECKING

from simple_zpl2 import ZPLDocument

from odoo import models

if TYPE_CHECKING:
    from ..models.product_import import ProductImport
    from ..models.product_template import ProductTemplate

logger = logging.getLogger(__name__)


class LabelMixin(models.AbstractModel):
    _name = "label.mixin"
    _description = "Label Mixin"

    LABEL_SIZE = {"width": 2.2, "height": 1.3}
    LABEL_TEXT_SIZE = {"large": 60, "medium": 35, "small": 20}
    LABEL_PADDING_Y = 10
    LABEL_PADDING_X = 10
    LABEL_CENTER_X = 220
    LABEL_BOTTOM_TEXT_Y = 210
    BARCODE_SIZE = 8

    def _print_labels(
        self,
        labels: list[str] | bytes,
        odoo_job_type: str,
        job_name: str,
    ) -> None:
        if isinstance(labels, list):
            if not isinstance(labels[0], str):
                logger.error("Invalid label data type")
            label_data = self.combine_labels_base64(labels)
        elif isinstance(labels, bytes):
            label_data = labels
        else:
            logger.error("Invalid label data type")
            return

        self.env["printnode.interface"].print_label(
            label_data,
            odoo_job_type=odoo_job_type,
            job_name=job_name,
        )

    def print_motor_labels(self, printer_job_type: str = "motor_label") -> None:
        report_name = "product_connect.report_motortemplatelabel4x2noprice"
        report_object = self.env["ir.actions.report"]._get_report_from_name(report_name)
        pdf_data, _ = report_object._render_qweb_pdf(report_name, res_ids=self.ids)

        self._print_labels(
            pdf_data,
            odoo_job_type=printer_job_type,
            job_name="Motor Label",
        )

    def print_bin_labels(self) -> None:
        if TYPE_CHECKING:
            assert isinstance(self, (ProductImport, ProductTemplate))
        unique_bins = [
            bin_location
            for bin_location in set(self.mapped("bin"))
            if bin_location and bin_location.strip().lower() not in ["", " ", "back"]
        ]
        unique_bins.sort()
        labels = []
        for product_bin in unique_bins:
            label_data = ["", "Bin: ", product_bin]
            label = self.generate_label_base64(label_data, barcode=product_bin)
            labels.append(label)
        self._print_labels(
            labels,
            odoo_job_type="product_label",
            job_name="Bin Label",
        )

    def print_product_labels(
        self, print_quantity: bool = False, printer_job_type: str = "product_label"
    ) -> None:
        labels = []
        for record in self:
            if TYPE_CHECKING:
                assert isinstance(record, (ProductImport, ProductTemplate))
            label_data = [
                f"SKU: {record.default_code}",
                "MPN: ",
                f"(SM){record.mpn}",
                f"Bin: {record.bin or '       '}",
                record.condition.title() if record.condition else "",
            ]
            quantity = getattr(record, "quantity", 1) if print_quantity else 1
            label = self.generate_label_base64(
                label_data,
                bottom_text=self.wrap_text(record.name, 50),
                barcode=record.default_code,
                quantity=quantity,
            )
            labels.append(label)
        self._print_labels(
            labels,
            odoo_job_type=printer_job_type,
            job_name="Product Label",
        )

    @staticmethod
    def wrap_text(text: str, max_line_length: int) -> list[str]:
        words = text.split(" ")
        lines = []
        current_line = []

        for word in words:
            if len(" ".join(current_line + [word])) > max_line_length:
                lines.append(" ".join(current_line))
                current_line = [word]
            else:
                current_line.append(word)

        if current_line:
            lines.append(" ".join(current_line))

        return lines

    def generate_label_base64(
        self,
        text: list[str] | str,
        bottom_text: str | list[str] | None = None,
        barcode: str | None = None,
        quantity: int = 1,
        print_date: bool = True,
    ) -> str:
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
    def combine_labels_base64(labels: list[str]) -> str:
        decoded_labels = [base64.b64decode(label).decode() for label in labels]
        combined_labels = "".join(decoded_labels)
        combined_labels_base64 = base64.b64encode(combined_labels.encode()).decode()
        return combined_labels_base64
