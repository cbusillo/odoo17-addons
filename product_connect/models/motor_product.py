from odoo import api, fields, models


class MotorProductTemplate(models.Model):
    _name = "motor.product.template"
    _description = "Motor Product Template"
    _order = "sequence, id"

    name = fields.Char(required=True)

    stroke = fields.Many2many("motor.stroke")
    configuration = fields.Many2many("motor.configuration")
    manufacturers = fields.Many2many("product.manufacturer", domain=[("is_motor_manufacturer", "=", True)])
    excluded_parts = fields.Many2many("motor.part.template")
    excluded_tests = fields.Many2many("motor.test.template")
    is_quantity_listing = fields.Boolean(default=False)
    include_year_in_name = fields.Boolean(default=True)
    include_hp_in_name = fields.Boolean(default=True)
    include_model_in_name = fields.Boolean(default=True)
    include_oem_in_name = fields.Boolean(default=True)

    part_type = fields.Many2one("product.type", index=True)
    qty_available = fields.Float()
    bin = fields.Char()
    weight = fields.Float()
    sequence = fields.Integer(default=10, index=True)


class MotorProductImage(models.Model):
    _name = "motor.product.image"
    _inherit = ["image.mixin"]
    _description = "Motor Product Images"

    index = fields.Integer(index=True, required=True, default=lambda self: self._get_next_index())
    product = fields.Many2one("motor.product", ondelete="cascade", required=True, index=True)

    def _get_next_index(self) -> int:
        last_index = self.search([("product", "=", self.product.id)], order="index desc", limit=1).index
        return (last_index or 0) + 1


class MotorProduct(models.Model):
    _name = "motor.product"
    _inherit = ["product.base"]
    _description = "Motor Product"
    _order = "sequence, part_type_name, id"

    images = fields.One2many("motor.product.image", "product")

    template = fields.Many2one("motor.product.template", required=True, ondelete="restrict", readonly=True)
    part_type = fields.Many2one(related="template.part_type", store=True)
    computed_name = fields.Char(compute="_compute_name", store=True)
    short_name = fields.Char(related="template.name")
    is_qty_listing = fields.Boolean(related="template.is_quantity_listing")

    reference_product = fields.Many2one("product.template", compute="_compute_reference_product", store=True)

    sequence = fields.Integer(related="template.sequence", index=True, store=True)
    excluded_parts = fields.Many2many("motor.part.template", related="template.excluded_parts")
    excluded_tests = fields.Many2many("motor.test.template", related="template.excluded_tests")

    is_dismantled = fields.Boolean(default=False)
    is_dismantled_qc = fields.Boolean(default=False)
    is_cleaned = fields.Boolean(default=False)
    is_cleaned_qc = fields.Boolean(default=False)
    is_pictured = fields.Boolean(default=False)
    is_pictured_qc = fields.Boolean(default=False)
    ready_to_list = fields.Boolean(compute="_compute_ready_to_list", store=True)

    def write(self, vals: dict) -> bool:
        result = super(MotorProduct, self).write(vals)

        if "images" in vals:
            for product in self:
                if product.image_count < 1:
                    product.is_pictured = False
                    product.is_pictured_qc = False

        if any(
            field in vals
            for field in [
                "is_dismantled",
                "is_dismantled_qc",
                "is_cleaned",
                "is_cleaned_qc",
                "is_pictured",
                "is_pictured_qc",
                "bin",
                "weight",
                "length",
                "width",
                "height",
            ]
        ):
            for product in self:
                product.motor.notify_changes()
        return result

    @api.depends("first_mpn")
    def _compute_reference_product(self) -> None:
        for motor_product in self:
            if not motor_product.first_mpn:
                motor_product.reference_product = False
                continue
            products = self.env["product.template"].search([])
            matching_products = products.filtered(
                lambda p: motor_product.first_mpn.lower() in p.mpn.lower().split(",") if p.mpn else False
            )
            latest_product = max(matching_products, key=lambda p: p.create_date, default=None)
            if latest_product:
                motor_product.reference_product = latest_product.id if latest_product else False

    @api.depends("name", "computed_name", "default_code")
    def _compute_display_name(self) -> None:
        for product in self:
            product.display_name = f"{product.default_code} - {product.name or product.computed_name}"

    @api.depends(
        "motor.manufacturer.name",
        "template.name",
        "mpn",
        "motor.year",
        "motor.horsepower",
        "template.include_year_in_name",
        "template.include_hp_in_name",
        "template.include_model_in_name",
        "template.include_oem_in_name",
    )
    def _compute_name(self) -> None:
        for product in self:
            name_parts = [
                product.motor.year if product.template.include_year_in_name else None,
                product.motor.manufacturer.name if product.motor.manufacturer else None,
                (product.motor.get_horsepower_formatted() if product.template.include_hp_in_name else None),
                product.motor.stroke.name,
                "Outboard",
                product.template.name,
                product.first_mpn if product.template.include_model_in_name else None,
                "OEM" if product.template.include_oem_in_name else None,
            ]
            new_computed_name = " ".join(part for part in name_parts if part)
            if not product.name or product.name == product.computed_name:
                product.name = new_computed_name
            product.computed_name = new_computed_name

    @api.depends(
        "is_dismantled",
        "is_dismantled_qc",
        "is_cleaned",
        "is_cleaned_qc",
        "is_pictured",
        "is_pictured_qc",
        "bin",
        "weight",
        "length",
        "width",
        "height",
    )
    def _compute_ready_to_list(self) -> None:
        for product in self:
            product.ready_to_list = all(
                [
                    product.is_dismantled,
                    product.is_dismantled_qc,
                    product.is_cleaned,
                    product.is_cleaned_qc,
                    product.is_pictured,
                    product.is_pictured_qc,
                    product.bin,
                    product.weight,
                    product.length,
                    product.width,
                    product.height,
                ]
            )

    def reset_name(self) -> None:
        for product in self:
            product.name = ""
            product._compute_name()
