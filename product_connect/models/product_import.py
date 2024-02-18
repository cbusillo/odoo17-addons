import base64
import logging
import io
from typing import Any, Self

import requests
from PIL import Image
import odoo
from odoo.exceptions import UserError
from ..mixins.product_labels import ProductLabelsMixin

_logger = logging.getLogger(__name__)


class ProductType(odoo.models.Model):
    _name = "product.type"
    _description = "Product Type"
    _sql_constraints = [
        ("name_uniq", "unique (name)", "Product Type name already exists !"),
    ]

    name = odoo.fields.Char(required=True, index=True)


class ProductImportImage(odoo.models.Model):
    _name = "product.import.image"
    _description = "Product Import Image"
    _order = "index"

    image_data = odoo.fields.Image(max_width=1920, max_height=1920)
    index = odoo.fields.Integer()
    product_id = odoo.fields.Many2one("product.import", ondelete="cascade")


class ProductImport(ProductLabelsMixin, odoo.models.Model):
    _name = "product.import"
    _description = "Product Import"
    _sql_constraints = [
        ("default_code_uniq", "unique (default_code)", "SKU already exists !"),
    ]

    default_code = odoo.fields.Char(
        string="SKU", required=True, copy=False, index=True, default=lambda self: "New"
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
    image_upload = odoo.fields.Json()
    image_ids = odoo.fields.One2many("product.import.image", "product_id")
    condition = odoo.fields.Selection(
        [
            ("used", "Used"),
            ("new", "New"),
            ("open_box", "Open Box"),
            ("broken", "Broken"),
            ("refurbished", "Refurbished"),
        ],
        default="used",
    )
    export_to_shopify = odoo.fields.Binary()

    def name_get(self) -> list[tuple[int, str]]:
        result = []
        for record in self:
            name = f"[{record.default_code}] {record.name or 'No Name Yet'}"
            result.append((record.id, name))
        return result

    @odoo.api.model_create_multi
    def create(self, vals_list: list[dict]) -> "ProductImport":
        product_template = self.env["product.template"]
        for vals in vals_list:
            if vals.get("default_code", "") == "New" or not vals.get("default_code"):
                while True:
                    new_sku = self.env["ir.sequence"].next_by_code("product.import")
                    if not product_template.search(
                        [("default_code", "=", new_sku)]
                    ) and not self.search([("default_code", "=", new_sku)]):
                        vals["default_code"] = new_sku
                        break

            for field in ["mpn", "bin"]:
                if field in vals:
                    if vals[field]:
                        vals[field] = vals[field].upper()

            temp_record = self.new(vals)
            if (
                temp_record.default_code != "New"
                and temp_record.default_code
                and temp_record.mpn
                and temp_record.condition
                and temp_record.quantity > 0
            ):
                temp_record.print_product_labels(print_quantity=True)
        return super().create(vals_list)

    def write(self, vals: dict) -> bool:
        for field in ["mpn", "bin"]:
            if field in vals:
                vals[field] = vals[field].upper()

        fields_of_interest = ["mpn", "condition", "quantity"]
        for record in self:
            if any(key in vals and not vals[key] for key in fields_of_interest):
                continue
            temp_data = record.copy_data()[0]
            temp_data.update(vals)
            temp_record = self.new(temp_data)

            if any(
                getattr(temp_record, key) != getattr(record, key)
                for key in fields_of_interest
            ):
                if all(
                    getattr(temp_record, key) or getattr(record, key)
                    for key in fields_of_interest
                ):
                    if (
                        getattr(temp_record, "quantity", 0) > 0
                        or getattr(record, "quantity", 0) > 0
                    ):
                        temp_record.print_product_labels(print_quantity=True)

        return super().write(vals)

    @odoo.api.model
    def load(self, fields: list[str], data: list[list[str]]) -> dict[str, Any]:
        for row in data:
            if "mpn" in fields:
                idx = fields.index("mpn")
                row[idx] = row[idx].upper()
            if "bin" in fields:
                idx = fields.index("bin")
                row[idx] = row[idx].upper()
        return super(ProductImport, self).load(fields, data)

    @odoo.api.onchange("image_upload")
    def _onchange_image_upload(self) -> None:
        if self.image_upload:
            image = self.env["product.import.image"].create(
                {
                    "image_data": self.image_upload["image"],
                    "index": self.image_upload["index"],
                    "product_id": self.id,
                }
            )
            self.image_ids |= image
            self.image_upload = False

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
                    f"A product with the same MPN already exists.  Its SKU is/are {existing_products_display}"
                )
        if self._origin.bin != self.bin and self.bin:
            if self.existing_bin() is False:
                self.print_bin_labels()

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
                "condition": product.condition,
            }
            existing_products[product.default_code] = product_to_add

        for product in product_templates:
            product_to_add = {
                "default_code": product.default_code,
                "bin": product.bin,
                "condition": product.condition,
            }
            existing_products[product.default_code] = product_to_add

        return list(existing_products.values())

    def products_from_mpn_condition_new(self) -> list[Self] | None:
        if self.mpn and self.condition == "new":
            existing_products = self._products_from_existing_records("mpn", self.mpn)
            existing_new_products = [
                product
                for product in existing_products
                if product["condition"] == "new"
            ]
            if existing_new_products:
                return existing_new_products
        return None

    def existing_bin(self) -> bool:
        if self.bin:
            existing_products = self._products_from_existing_records("bin", self.bin)
            if existing_products:
                return True
        return False

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
            _logger.warning("Missing data for records: %s", missing_data_records)

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
                    _logger.warning(
                        "Skipping import of record with SKU: %s due to image error.",
                        record.default_code,
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
                "condition": record.condition or product.condition,
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
            sorted_images = record.image_ids.sorted(key=lambda r: r.index)

            for image in sorted_images:
                self.env["product.image"].create(
                    {
                        "image_1920": image.image_data,
                        "product_tmpl_id": product.product_tmpl_id.id,
                        "name": current_index,
                    }
                )
                current_index += 1
            record.unlink()
        return {"type": "ir.actions.client", "tag": "reload"}

    def open_product_import_wizard(self) -> dict[str, str | dict[str, int]]:
        return {
            "name": "Calculate Costs",
            "type": "ir.actions.act_window",
            "res_model": "product.import.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_selected_product_ids": self.ids},
        }
