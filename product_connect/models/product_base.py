import logging
import re
from datetime import timedelta
from typing import Any

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)


class ProductType(models.Model):
    _name = "product.type"
    _description = "Part Type"
    _sql_constraints = [
        ("name_uniq", "unique (name)", "Part Type name already exists !"),
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
    ]
    _description = "Product Base"
    _order = "create_date desc"
    _sql_constraints = [
        ("default_code_uniq", "unique(default_code)", "SKU must be unique."),
    ]

    name = fields.Char(index=True)
    motor = fields.Many2one("motor", ondelete="restrict", readonly=True)
    default_code = fields.Char(
        "SKU", index=True, copy=False, required=True, readonly=True, default=lambda self: self.get_next_sku()
    )
    create_date = fields.Datetime(index=True)

    images = fields.One2many("product.image", "product_tmpl_id")
    image_count = fields.Integer(compute="_compute_image_count")
    image_icon = fields.Binary(compute="_compute_icon", store=True)

    mpn = fields.Char(string="MPN", index=True)
    first_mpn = fields.Char(compute="_compute_first_mpn", store=True)
    manufacturer = fields.Many2one("product.manufacturer", index=True)
    part_type = fields.Many2one("product.type", index=True)
    part_type_name = fields.Char(related="part_type.name", store=True, index=True, string="Part Type Name")
    condition = fields.Many2one("product.condition", index=True)

    length = fields.Integer()
    width = fields.Integer()
    height = fields.Integer()
    weight = fields.Float()

    bin = fields.Char(index=True)
    qty_available = fields.Float(string="Quantity")

    list_price = fields.Float(string="Price")
    standard_price = fields.Float(string="Cost")

    sales_description = fields.Text(string="Descr")

    active = fields.Boolean(default=True)
    has_recent_messages = fields.Boolean(compute="_compute_has_recent_messages", store=True)
    is_listable = fields.Boolean(default=False)

    # noinspection PyShadowingNames
    @api.model
    def read_group(
        self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True
    ) -> list[dict[str, Any]]:
        groups = super(ProductBase, self).read_group(
            domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy
        )
        fields_to_sum_with_qty = {"list_price", "standard_price"}
        if fields_to_sum_with_qty.intersection(fields):
            for group in groups:
                if "__domain" in group:
                    group["list_price"] = sum(
                        product["list_price"] * product["qty_available"] for product in self.search(group["__domain"])
                    )
                    group["standard_price"] = sum(
                        product["standard_price"] * product["qty_available"]
                        for product in self.search(group["__domain"])
                    )

        return groups

    @api.constrains("default_code")
    def _check_sku(self) -> None:
        for product in self:
            if not product.default_code:
                continue
            if not re.match(r"^\d{4,8}$", str(product.default_code)):
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
        for product in self:
            fields_to_check = [product.length, product.width, product.height]
            for field_value in fields_to_check:
                if field_value and len(str(abs(field_value))) > 2:
                    raise ValidationError("Dimensions cannot exceed 2 digits.")

    @api.depends("images.image_1920")
    def _compute_icon(self) -> None:
        for product in self:
            product.image_icon = product.images[0].image_128 if product.images else None

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
        for product in self:
            name = f"[{product.default_code}] {product.name or 'No Name Yet'}"
            result.append((product.id, name))
        return result

    @api.onchange("bin", "mpn")
    def _onchange_format_fields_upper(self) -> None:
        for product in self:
            product.mpn = product.mpn.upper() if product.mpn else False
            product.bin = product.bin.upper() if product.bin else False

    def _products_from_existing_products(self, field_name: str, field_value: str) -> list[dict[str, str]]:
        is_new_product = isinstance(self.id, models.NewId)
        if is_new_product:
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
            existing_products = self._products_from_existing_products("mpn", self.first_mpn)
            existing_new_products = [product for product in existing_products if product["condition"] == "new"]
            if existing_new_products:
                return existing_new_products
        return None

    def import_to_products(self) -> None:
        if self._name in ["product.template", "product.product"]:
            raise UserError("This method is not available for Odoo base products.")

        missing_data_products = self.filtered(
            lambda current: not (
                current.default_code
                and current.name
                and current.sales_description
                and current.standard_price
                and current.list_price
                and current.qty_available
                and current.bin
                and current.manufacturer
            )
            or len(current.images) == 0
        )
        if missing_data_products:
            message = f"Missing data for product(s).  Please fill in all required fields for SKUs {' '.join([p.default_code for p in missing_data_products])} ."
            _logger.warning(message)
            for product in missing_data_products:
                product.message_post(
                    body=message,
                    subject="Import Error (Missing Data)",
                    message_type="notification",
                    subtype_xmlid="mail.mt_note",
                    partner_ids=[self.env.user.partner_id.id],
                )

        for product in self.filtered(lambda current: current.is_listable) - missing_data_products:
            existing_products_with_mpn = product.products_from_mpn_condition_new()
            if existing_products_with_mpn:
                existing_products_display = [
                    f"{product['default_code']} - {product['bin']}" for product in existing_products_with_mpn
                ]
                raise UserError(
                    f"A product with the same MPN already exists.  Its SKU is/are {existing_products_display}"
                )
            existing_product = self.env["product.product"].search(
                [("default_code", "=", product.default_code)], limit=1
            )
            if existing_product:
                raise UserError(
                    f"A product with the same SKU already exists.  Its SKU is {existing_product.default_code}"
                )

            new_product = self.env["product.product"].create(
                {
                    "default_code": product.default_code,
                    "mpn": product.mpn,
                    "manufacturer": product.manufacturer.id,
                    "bin": product.bin,
                    "name": product.name,
                    "description_sale": product.sales_description,
                    "part_type": product.part_type.id,
                    "weight": product.weight,
                    "list_price": product.list_price,
                    "standard_price": product.standard_price,
                    "condition": product.condition.id,
                    "detailed_type": "product",
                    "is_published": True,
                    "shopify_next_export": True,
                    "motor": product.motor.id,
                    "length": product.length,
                    "width": product.width,
                    "height": product.height,
                }
            )
            new_product.update_quantity(product.qty_available)

            sorted_images = product.images.sorted(key=lambda r: r.index)

            for image in sorted_images:
                if not image.image_1920:
                    continue

                self.env["product.image"].create(
                    {
                        "image_1920": image.image_1920,
                        "product_tmpl_id": new_product.product_tmpl_id.id,
                        "name": image.index,
                    }
                )
                image.unlink()
            product.unlink()
