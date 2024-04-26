import base64

from odoo import _, fields, models
from odoo.exceptions import UserError


class ProductLabelLayout(models.TransientModel):
    _inherit = "product.label.layout"

    print_format = fields.Selection(
        selection_add=[
            ("2x1", "2.25 x 1.25 QR Product"),
            ("2x1bin", "2.25 x 1.25 QR Bin"),
        ],
        ondelete={
            "2x1": "set default",
            "2x1bin": "set default",
        },
        default="2x1",
    )

    def _prepare_report_data(self) -> tuple[str, dict[str, any]]:
        xml_id, data = super()._prepare_report_data()

        products_data = []
        if "bin" in self.print_format:
            xml_id = "product_connect.report_product_template_label_2x1_bin_noprice"

            product_records = (
                self.product_ids if self.product_ids else self.product_tmpl_ids
            )
            bins = set()
            for product_record in product_records:
                if product_record.bin not in bins:
                    bins.add(product_record.bin)
                    products_data.append(
                        {"bin": product_record.bin, "current_date": fields.Date.today()}
                    )

        elif self.print_format == "2x1":
            xml_id = "product_connect.report_product_template_label_2x1_noprice"

            product_records = (
                self.product_ids if self.product_ids else self.product_tmpl_ids
            )

            for product_record in product_records:
                products_data.append(
                    {
                        "current_date": fields.Date.today(),
                        "default_code": product_record.default_code,
                        "name": product_record.name,
                        "mpn": (
                            product_record.mpn.split(",")[0]
                            if product_record.mpn
                            else ""
                        ),
                        "bin": product_record.bin,
                        "condition": (
                            product_record.condition.title()
                            if product_record.condition
                            else ""
                        ),
                        "quantity": data["quantity_by_product"].get(
                            product_record.id, 1
                        ),
                    }
                )
        data.update({"products_data": products_data})
        return xml_id, data

    def process(self) -> dict[str, any]:
        custom_formats = ["2x1", "2x1bin", "4x2motor"]
        if self.print_format not in custom_formats or True:
            return super().process()

        self.ensure_one()
        xml_id, data = self._prepare_report_data()
        if not xml_id:
            raise UserError(
                _("Unable to find report template for %s format", self.print_format)
            )
        report = self.env.ref(xml_id)
        report_pdf_content, content_type = report._render_qweb_pdf(xml_id, data=data)
        report_pdf = base64.b64encode(report_pdf_content).decode()
        report_action = report.report_action(None, data=data)
        report_action["context"] = {"report_pdf": report_pdf}

        return report_action

    # def process(self):
    #     action = super(ProductLabelLayout, self).process()
    #     self.ensure_one()
    #     xml_id, data = self._prepare_report_data()
    #     if not xml_id:
    #         raise UserError(
    #             _("Unable to find report template for %s format", self.print_format)
    #         )
    #     report_action = self.env.ref(xml_id).report_action(None, data=data)
    #     report_action.update({"close_on_report_download": True})
    #     return action
