import base64
import io
import logging
from datetime import timedelta

import odoo
import requests
from PIL import Image
from odoo.exceptions import UserError

from ..mixins.label import LabelMixin

_logger = logging.getLogger(__name__)


class ProductImportImage(odoo.models.Model):
    _name = "product.import.image"
    _inherit = ["image.mixin"]
    _description = "Product Import Image"
    _order = "index"
    # noinspection SqlResolve
    _sql_constraints = [
        ("index_uniq", "unique (index, product)", "Index must be unique per product!"),
    ]

    index = odoo.fields.Integer(index=True, required=True)
    product = odoo.fields.Many2one(
        "product.import", ondelete="cascade", required=True, index=True
    )


class ProductImport(LabelMixin, odoo.models.Model):
    _name = "product.import"
    _description = "Product Import"
    _inherit = ["mail.thread"]
    _sql_constraints = [
        ("default_code_uniq", "unique (default_code)", "SKU already exists !")
    ]

    default_code = odoo.fields.Char(
        string="SKU",
        required=True,
        copy=False,
        index=True,
        readonly=True,
        default=lambda self: self.env["product.template"].get_next_sku(),
    )
    mpn = odoo.fields.Char(string="MPN", index=True)
    manufacturer = odoo.fields.Many2one("product.manufacturer", index=True)
    manufacturer_barcode = odoo.fields.Char(index=True)
    quantity = odoo.fields.Integer()
    bin = odoo.fields.Char(index=True)
    lot_number = odoo.fields.Char(index=True)
    name = odoo.fields.Char(index=True)
    description = odoo.fields.Char()
    product_type = odoo.fields.Many2one("product.type", index=True)
    weight = odoo.fields.Float()
    price = odoo.fields.Float()
    cost = odoo.fields.Float()
    image_1_url = odoo.fields.Char(string="Image 1 URL")
    images = odoo.fields.One2many("product.import.image", "product")
    image_count = odoo.fields.Integer(compute="_compute_image_count")
    icon = odoo.fields.Binary(compute="_compute_icon", store=True)
    condition = odoo.fields.Many2one(
        "product.condition",
        index=True,
        default=lambda self: self.env.ref(
            "product_connect.product_condition_used", raise_if_not_found=False
        ),
    )
    has_recent_messages = odoo.fields.Boolean(
        compute="_compute_has_recent_messages", store=True
    )

    def name_get(self) -> list[tuple[int, str]]:
        result = []
        for record in self:
            name = f"[{record.default_code}] {record.name or 'No Name Yet'}"
            result.append((record.id, name))
        return result

    @odoo.api.depends("message_ids")
    def _compute_has_recent_messages(self) -> None:
        for product in self:
            recent_messages = product.message_ids.filtered(
                lambda m: odoo.fields.Datetime.now() - m.create_date
                < timedelta(minutes=30)
            )
            product.has_recent_messages = bool(recent_messages)

    @odoo.api.depends("images.image_1920")
    def _compute_icon(self) -> None:
        for record in self:
            record.icon = record.images[0].image_128 if record.images else None

    def _compute_image_count(self) -> None:
        for motor in self:
            motor.image_count = len(
                [image for image in motor.images if image.image_1920]
            )

    @odoo.api.onchange("bin", "mpn")
    def _format_fields_upper(self) -> None:
        for record in self:
            record.mpn = record.mpn.upper() if record.mpn else False
            record.bin = record.bin.upper() if record.bin else False

    @odoo.api.onchange("default_code", "mpn", "condition", "bin", "quantity")
    def _onchange_product_details(self) -> None:
        if self._origin.mpn != self.mpn or self._origin.condition != self.condition:
            existing_products = self.products_from_mpn_condition_new()
            if existing_products:
                existing_products_display = [
                    f"{product['default_code']} - {product['bin']}"
                    for product in existing_products
                ]
                raise UserError(
                    f"A product with the same MPN already exists.  Its SKU is {existing_products_display}"
                )

    def _products_from_existing_records(
        self, field_name: str, field_value: str
    ) -> list[dict[str, str]]:
        is_new_record = isinstance(self.id, odoo.models.NewId)
        if is_new_record:
            product_imports = self.env["product.import"].search(
                [(field_name, "=", field_value)]
            )
        else:
            product_imports = self.env["product.import"].search(
                [
                    (field_name, "=", field_value),
                    ("id", "!=", self.id),
                ]
            )
        product_templates = self.env["product.template"].search(
            [(field_name, "=", field_value)]
        )

        existing_products = {}
        for product in product_imports:
            product_to_add = {
                "default_code": product.default_code,
                "bin": product.bin,
                "condition": product.condition.id,
            }
            existing_products[product.default_code] = product_to_add

        for product in product_templates:
            product_to_add = {
                "default_code": product.default_code,
                "bin": product.bin,
                "condition": product.condition.id,
            }
            existing_products[product.default_code] = product_to_add

        return list(existing_products.values())

    def products_from_mpn_condition_new(self) -> list[dict[str, str]] | None:
        if self.mpn and self.condition.code == "new":
            existing_products = self._products_from_existing_records("mpn", self.mpn)
            existing_new_products = [
                product
                for product in existing_products
                if product["condition"] == "new"
            ]
            if existing_new_products:
                return existing_new_products
        return None

    def get_image_from_url(self, url: str) -> bytes | bool:
        if not url:
            return False
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
            }
            session = requests.Session()
            session.headers.update(headers)
            response = session.get(url, timeout=10)
            try:
                Image.open(io.BytesIO(response.content))
                image_base64 = base64.b64encode(response.content)
                return image_base64
            except IOError:
                _logger.error(
                    "The binary data could not be decoded as an image. URL: %s", url
                )

        except requests.exceptions.Timeout:
            _logger.error(
                "Timeout Error getting image from SKU: %s, URL: %s",
                self.default_code,
                url,
            )

        except requests.exceptions.RequestException:
            _logger.error(
                "Request Error getting image from SKU: %s, URL: %s",
                self.default_code,
                url,
            )
        return False

    def import_to_products(self) -> dict[str, str]:
        missing_data_records = self.filtered(
            lambda current_record: not current_record.default_code
            or not current_record.name
        )
        if missing_data_records:
            message = f"Missing data for records.  Please fill in all required fields for SKUs {' '.join([p.default_code for p in missing_data_records])} ."
            _logger.warning(message)
            for record in missing_data_records:
                record.message_post(
                    body=message,
                    subject="Import Error (Missing Data)",
                    message_type="notification",
                    subtype_xmlid="mail.mt_note",
                    partner_ids=[self.env.user.partner_id.id],
                )

        for record in self - missing_data_records:
            existing_products = record.products_from_mpn_condition_new()
            if existing_products:
                existing_products_display = [
                    f"{product['default_code']} - {product['bin']}"
                    for product in existing_products
                ]
                raise UserError(
                    f"A product with the same MPN already exists.  Its SKU is/are {existing_products_display}"
                )
            product = self.env["product.product"].search(
                [("default_code", "=", record.default_code)], limit=1
            )
            image_from_url_data = None
            if record.image_1_url:
                image_from_url_data = record.get_image_from_url(record.image_1_url)
                if not image_from_url_data:
                    message = (
                        f"Error getting image from URL for SKU: {record.default_code}"
                    )
                    _logger.warning(message)
                    record.message_post(
                        body=message,
                        subject="Import Error (Image)",
                        message_type="notification",
                        subtype_xmlid="mail.mt_note",
                        partner_ids=[self.env.user.partner_id.id],
                    )

                    continue

            product_data = {
                "default_code": record.default_code or product.default_code,
                "mpn": record.mpn or product.mpn,
                "manufacturer": record.manufacturer.id or product.manufacturer.id,
                "bin": record.bin or product.bin,
                "name": record.name or product.name,
                "description_sale": record.description or product.description_sale,
                "part_type": record.product_type.id or product.part_type.id,
                "weight": record.weight if record.weight > 0 else product.weight,
                "list_price": record.price if record.price > 0 else product.list_price,
                "standard_price": (
                    record.cost if record.cost > 0 else product.standard_price
                ),
                "condition": record.condition.id or product.condition.id,
                "detailed_type": "product",
                "is_published": True,
                "shopify_next_export": True,
                "manufacturer_barcode": record.manufacturer_barcode
                or product.manufacturer_barcode,
                "lot_number": record.lot_number or product.lot_number,
            }
            if product:
                product.write(product_data)
            else:
                product = self.env["product.product"].create(product_data)
            if record.quantity > 0:
                product.update_quantity(record.quantity)

            current_images = self.env["product.image"].search(
                [("product_tmpl_id", "=", product.product_tmpl_id.id)]
            )

            current_index = 1
            for image in current_images:
                if int(image.name or 0) > current_index:
                    current_index = int(image.name or 1)

            if image_from_url_data:
                self.env["product.image"].create(
                    {
                        "image_1920": image_from_url_data,
                        "product_tmpl_id": product.product_tmpl_id.id,
                        "name": current_index,
                    }
                )
                current_index += 1
            sorted_images = record.images.sorted(key=lambda r: r.index)

            for image in sorted_images:
                if not image.image_1920:
                    continue

                self.env["product.image"].create(
                    {
                        "image_1920": image.image_1920,
                        "product_tmpl_id": product.product_tmpl_id.id,
                        "name": current_index,
                    }
                )
                current_index += 1
            record.unlink()
        return {
            "type": "ir.actions.act_window",
            "view_mode": self._context.get("view_mode", "tree,form"),
            "res_model": self._name,
        }

    def open_product_import_wizard(self) -> dict[str, str | dict[str, int]]:
        return {
            "name": "Calculate Costs",
            "type": "ir.actions.act_window",
            "res_model": "product.import.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_selected_product_ids": self.ids},
        }
