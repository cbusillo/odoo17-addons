import logging
import re
from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)


class ProductType(models.Model):
    _name = "product.type"
    _description = "Product Type"
    _sql_constraints = [
        ("name_uniq", "unique (name)", "Product Type name already exists !"),
    ]

    name = fields.Char(required=True, index=True)
    ebay_category_id = fields.Integer(string="eBay Category ID", index=True)

    products = fields.One2many("product.template", "part_type")
    products_import = fields.One2many("product.import", "part_type")
    motor_products = fields.One2many("motor.product", "part_type")


class ProductCondition(models.Model):
    _name = "product.condition"
    _description = "Product Condition"
    _sql_constraints = [("name_uniq", "unique (name)", "Product Condition name already exists !")]

    name = fields.Char(required=True, index=True)
    code = fields.Char(required=True, index=True, readonly=True)
    ebay_condition_id = fields.Integer(string="eBay Condition ID", index=True)

    products = fields.One2many("product.template", "condition")
    products_import = fields.One2many("product.import", "condition")
    motor_products = fields.One2many("motor.product", "condition")


class ProductBase(models.AbstractModel):
    _name = "product.base"
    _inherit = [
        "mail.thread",
        "label.mixin",
        "image.mixin",
    ]
    _description = "Product Base"
    _order = "create_date desc"
    _sql_constraints = [
        ("default_code_uniq", "unique(default_code)", "SKU must be unique."),
    ]

    name = fields.Char(required=True, index=True)
    default_code = fields.Char(
        "SKU", index=True, copy=False, required=True, readonly=True, default=lambda self: self.get_next_sku()
    )
    create_date = fields.Datetime(index=True)

    images = fields.One2many("product.image", "product_tmpl_id")
    image_count = fields.Integer(compute="_compute_image_count")
    icon = fields.Binary(compute="_compute_icon", store=True)

    mpn = fields.Char(string="MPN", index=True)
    first_mpn = fields.Char(compute="_compute_first_mpn", store=True)
    manufacturer = fields.Many2one("product.manufacturer", index=True)
    part_type = fields.Many2one("product.type", index=True)
    condition = fields.Many2one("product.condition", index=True)

    length = fields.Integer()
    width = fields.Integer()
    height = fields.Integer()
    weight = fields.Float()

    bin = fields.Char(index=True)
    qty_available = fields.Float()

    list_price = fields.Float(string="Sale Price")
    standard_price = fields.Float(string="Cost")

    description = fields.Text()

    active = fields.Boolean(default=True)
    has_recent_messages = fields.Boolean(compute="_compute_has_recent_messages", store=True)

    @api.constrains("default_code")
    def _check_sku(self) -> None:
        for record in self:
            if not record.default_code:
                continue
            if not re.match(r"^\d{4,8}$", str(record.default_code)):
                raise ValidationError(_("SKU must be 4-8 digits."))

    def get_next_sku(self) -> str:
        sequence = self.env["ir.sequence"].search([("code", "=", "product.template.default_code")])
        padding = sequence.padding
        max_sku = "9" * padding
        while (new_sku := self.env["ir.sequence"].next_by_code("product.template.default_code")) <= max_sku:
            if not (
                self.env["motor.product"].search_count([("default_code", "=", new_sku)])
                or self.env["product.template"].search_count([("default_code", "=", new_sku)])
                or self.env["product.import"].search_count([("default_code", "=", new_sku)])
            ):
                return new_sku
        raise ValidationError("SKU limit reached.")

    @api.constrains("length", "width", "height")
    def _check_dimension_values(self) -> None:
        for record in self:
            fields_to_check = [record.length, record.width, record.height]
            for field_value in fields_to_check:
                if field_value and len(str(abs(field_value))) > 2:
                    raise ValidationError("Dimensions cannot exceed 2 digits.")

    @api.depends("images.image_1920")
    def _compute_icon(self) -> None:
        for record in self:
            record.icon = record.images[0].image_128 if record.images else None

    @api.depends("mpn")
    def _compute_first_mpn(self) -> None:
        for product in self:
            product.first_mpn = product.mpn.split(",")[0].strip() if product.mpn else ""

    def _compute_image_count(self) -> None:
        for product in self:
            product.image_count = len([image for image in product.images if image.image_1920])

    @api.depends("message_ids")
    def _compute_has_recent_messages(self) -> None:
        for product in self:
            recent_messages = product.message_ids.filtered(
                lambda m: fields.Datetime.now() - m.create_date < timedelta(minutes=30)
                and m.subject
                and "Import Error" in m.subject
            )
            product.has_recent_messages = bool(recent_messages)

    def name_get(self) -> list[tuple[int, str]]:
        result = []
        for record in self:
            name = f"[{record.default_code}] {record.name or 'No Name Yet'}"
            result.append((record.id, name))
        return result

    @api.onchange("bin", "mpn")
    def _onchange_format_fields_upper(self) -> None:
        for record in self:
            record.mpn = record.mpn.upper() if record.mpn else False
            record.bin = record.bin.upper() if record.bin else False

    def _products_from_existing_records(self, field_name: str, field_value: str) -> list[dict[str, str]]:
        is_new_record = isinstance(self.id, models.NewId)
        if is_new_record:
            product_imports = self.search([(field_name, "=", field_value)])
        else:
            product_imports = self.search(
                [
                    (field_name, "=", field_value),
                    ("id", "!=", self.id),
                ]
            )
        product_templates = self.env["product.template"].search([(field_name, "=", field_value)])

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
            existing_products = self._products_from_existing_records("mpn", self.first_mpn)
            existing_new_products = [product for product in existing_products if product["condition"] == "new"]
            if existing_new_products:
                return existing_new_products
        return None

    def import_to_products(self) -> dict[str, str]:
        missing_data_records = self.filtered(
            lambda current_record: not current_record.default_code or not current_record.name
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
                    f"{product['default_code']} - {product['bin']}" for product in existing_products
                ]
                raise UserError(
                    f"A product with the same MPN already exists.  Its SKU is/are {existing_products_display}"
                )
            product = self.env["product.product"].search([("default_code", "=", record.default_code)], limit=1)

            product_data = {
                "default_code": record.default_code or product.default_code,
                "mpn": record.mpn or product.mpn,
                "manufacturer": record.manufacturer.id or product.manufacturer.id,
                "bin": record.bin or product.bin,
                "name": record.name or product.name,
                "description_sale": record.description or product.description_sale,
                "part_type": record.part_type.id or product.part_type.id,
                "weight": record.weight if record.weight > 0 else product.weight,
                "list_price": record.list_price if record.list_price > 0 else product.list_price,
                "standard_price": (record.standard_price if record.standard_price > 0 else product.standard_price),
                "condition": record.condition.id or product.condition.id,
                "detailed_type": "product",
                "is_published": True,
                "shopify_next_export": True,
            }
            if product:
                product.write(product_data)
            else:
                product = self.env["product.product"].create(product_data)
            if record.qty_available > 0:
                product.update_quantity(record.qty_available)

            current_images = self.env["product.image"].search([("product_tmpl_id", "=", product.product_tmpl_id.id)])

            current_index = 1
            for image in current_images:
                if int(image.name or 0) > current_index:
                    current_index = int(image.name or 1)

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
