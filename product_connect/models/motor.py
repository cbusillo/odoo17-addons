import base64
import re
from io import BytesIO
from typing import Any, Self

import qrcode  # type: ignore
from odoo.exceptions import ValidationError

from odoo import _, api, fields, models
from ..mixins.label import LabelMixin
from ..utils import constants


class Motor(models.Model, LabelMixin):
    _name = "motor"
    _description = "Motor Information"
    _order = "id desc"

    # Basic Info
    active = fields.Boolean(default=True)
    motor_number = fields.Char()
    technician = fields.Many2one(
        "res.users", string="Tech Name",
        domain="['|', ('id', '=', technician), '&', ('is_technician', '=', True), ('active', '=', True)]",
        ondelete="restrict",
    )
    signature = fields.Binary()
    manufacturer = fields.Many2one("product.manufacturer", domain="[('is_motor_manufacturer', '=', True)]")
    horsepower = fields.Float(digits=(3, 1), string="HP")
    horsepower_formatted = fields.Char(compute="_compute_horsepower_formatted")
    stroke = fields.Many2one("motor.stroke")
    configuration = fields.Many2one("motor.configuration")
    model = fields.Char()
    sub_model = fields.Char()
    serial_number = fields.Char()

    @api.model
    def _get_years(self) -> list[tuple[str, str]]:
        return [
            (str(year), str(year))
            for year in range(fields.Date.today().year + 1, 1960, -1)
        ]

    year = fields.Selection(_get_years, string="Model Year")
    hours = fields.Float(compute="_compute_hours")
    shaft_length = fields.Char(compute="_compute_shaft_length")
    color = fields.Many2one("product.color", domain="[('applicable_tags.name', '=', 'Motors')]")
    cost = fields.Float()

    is_tag_readable = fields.Selection(constants.YES_NO_SELECTION, default=constants.YES)
    notes = fields.Text()
    has_notes = fields.Boolean(compute="_compute_has_notes", store=True)
    images = fields.One2many("motor.image", "motor")
    icon = fields.Binary(compute="_compute_icon", store=True)
    parts = fields.One2many("motor.part", "motor")
    missing_parts = fields.One2many("motor.part", "motor", domain=[("is_missing", "=", True)])
    missing_parts_names = fields.Char(compute="_compute_missing_parts_names", store=True)
    tests = fields.One2many("motor.test", "motor")
    test_sections = fields.One2many("motor.test.section", "motor")
    basic_tests = fields.One2many("motor.test", "motor", domain=[("template.stage", "=", "basic")])
    extended_tests = fields.One2many("motor.test", "motor", domain=[("template.stage", "=", "extended")])

    compression = fields.One2many("motor.compression", "motor")
    compression_formatted_html = fields.Html(compute="_compute_compression_formatted_html")
    hide_compression_page = fields.Boolean(compute="_compute_hide_compression_page", store=True)
    products = fields.One2many("motor.product", "motor")

    stage = fields.Selection(constants.MOTOR_STAGE_SELECTION, default="basic_info", required=True)

    @api.model_create_multi
    def create(self, vals_list: list[dict]) -> Self:
        vals_list = [self._sanitize_vals(vals) for vals in vals_list]

        records = super().create(vals_list)
        for record in records:
            record.motor_number = f"M-{record.id}"
            record._create_default_images(record)

            record._create_motor_parts()
            record._create_motor_tests()

        return records

    def write(self, vals) -> Self:
        if self.env.context.get("_stage_updating"):
            return super().write(vals)
        vals = self._sanitize_vals(vals)

        result = super().write(vals)
        for record in self.with_context(_stage_updating=True):
            record._update_stage()
            # record._create_motor_products()
        return result

    def _compute_compression_formatted_html(self) -> None:
        for motor in self:
            lines = [
                f"Cylinder: {c.cylinder_number} Compression: {c.compression_psi} PSI" for c
                in motor.compression
            ]
            motor.compression_formatted_html = "<br/>".join(lines)

    def _compute_missing_parts_names(self) -> None:
        for motor in self:
            missing_parts_names = ", ".join(
                part.name for part in motor.missing_parts if part.name
            )
            motor.missing_parts_names = missing_parts_names

    def _compute_shaft_length(self) -> None:
        for motor in self:
            shaft_length = motor.tests.filtered(
                lambda t: "shaft" in t.template.name.lower() and "length" in t.template.name.lower()
            )
            motor.shaft_length = shaft_length.selection_result if shaft_length else ""

    def _compute_hours(self) -> None:
        for motor in self:
            hours = motor.tests.filtered(
                lambda t: "engine" in t.template.name.lower() and "hours" in t.template.name.lower())
            motor.hours = hours.numeric_result if hours else 0

    @api.depends("notes")
    def _compute_has_notes(self) -> None:
        for motor in self:
            motor.has_notes = bool(motor.notes)

    @api.depends("images")
    def _compute_icon(self) -> None:
        for motor in self:
            motor.icon = motor.images[0].image_128 if motor.images else False

    @api.depends("horsepower")
    def _compute_horsepower_formatted(self) -> None:
        for motor in self:
            motor.horsepower_formatted = motor.get_horsepower_formatted()

    @api.depends(
        "motor_number", "manufacturer", "model", "year", "serial_number", "horsepower"
    )
    def _compute_display_name(self) -> None:
        for motor in self:
            serial_number = (
                f" - {motor.serial_number}" if motor.serial_number else None
            )

            name_parts = [
                motor.motor_number,
                motor.year,
                motor.manufacturer.name,
                motor.get_horsepower_formatted(),
                motor.model,
                serial_number,
            ]
            name = " ".join(part for part in name_parts if part)

            if name:
                motor.display_name = name

    @api.depends("parts.is_missing", "parts.template.hide_compression_page")
    def _compute_hide_compression_page(self) -> None:
        for motor in self:
            hide_parts = motor.parts.filtered(
                lambda p: p.is_missing and p.template.hide_compression_page
            )
            motor.hide_compression_page = bool(hide_parts)

    def generate_qr_code(self) -> str:
        qr_code = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=20,
        )
        qr_code.add_data(self.motor_number)
        qr_code.make()

        qr_image = qr_code.make_image(fill_color="black", back_color="white")

        with BytesIO() as qr_image_buffer:
            qr_image.save(qr_image_buffer)
            qr_image_base64 = base64.b64encode(qr_image_buffer.getvalue()).decode()

        return qr_image_base64

    def get_horsepower_formatted(self) -> str:
        if not self.horsepower:
            return ""

        if self.horsepower.is_integer():
            return f"{int(self.horsepower)} HP"
        else:
            return f"{self.horsepower} HP"

    @api.constrains("horsepower")
    def _check_horsepower(self) -> None:
        for record in self:
            if not isinstance(record.horsepower, float) or (
                    record.horsepower and not (0.0 <= record.horsepower <= 600.0)
            ):
                raise ValidationError(_("Horsepower must be between 1 and 600."))

    @staticmethod
    def _sanitize_vals(vals: dict[str, Any]) -> dict[str, Any]:
        if "year" in vals and vals["year"]:
            vals["year"] = "".join(char for char in vals["year"] if char.isdigit())
        if "model" in vals and vals["model"]:
            vals["model"] = vals["model"].upper()
        if "serial_number" in vals and vals["serial_number"]:
            vals["serial_number"] = vals["serial_number"].upper()
        return vals

    def _create_motor_tests(self) -> None:
        test_templates = self.env["motor.test.template"].search([])
        test_vals = []
        for template in test_templates:
            test_vals.append(
                {
                    "motor": self.id,
                    "template": template.id,
                }
            )
        if test_vals:
            self.env["motor.test"].create(test_vals)

    def _create_motor_parts(self) -> None:
        part_templates = self.env["motor.part.template"].search([])
        part_vals = []
        for template in part_templates:
            part_vals.append(
                {
                    "motor": self.id,
                    "template": template.id,
                }
            )
        if part_vals:
            self.env["motor.part"].create(part_vals)

    def _create_motor_products(self) -> None:
        product_templates = self.env["motor.product.template"].search([])
        current_product_ids = set(self.products.ids)  # Existing product IDs related to this motor

        for product_template in product_templates:
            if product_template.stroke and self.stroke not in product_template.stroke:
                continue
            if product_template.configuration and self.configuration not in product_template.configuration:
                continue
            if product_template.manufacturers and self.manufacturer not in product_template.manufacturers:
                continue

            excluded_parts_ids = product_template.excluded_parts.mapped('id')
            if set(self.parts.mapped('template.id')) & set(excluded_parts_ids):
                continue

            excluded_tests_ids = product_template.excluded_tests.mapped('id')
            if set(self.tests.mapped('template.id')) & set(excluded_tests_ids):
                continue

            product_data = {
                'motor': self.id,
                'template': product_template.id,
            }

            existing_product = self.products.filtered(
                lambda p: p.template == product_template)

            if existing_product:
                current_product_ids.discard(existing_product.id)
            else:
                product_data["quantity"] = product_template.quantity or 1
                product_data["bin"] = product_template.bin
                product_data["weight"] = product_template.weight
                self.env['motor.product'].create(product_data)

        if current_product_ids:
            self.products.filtered(lambda p: p.id in current_product_ids).unlink()

    def _get_cylinder_count(self) -> int:
        match = re.search(r"\d+", self.configuration.name)
        if match:
            return int(match.group())
        return 0

    @api.onchange("configuration")
    def _onchange_motor_configuration(self) -> None:
        if not self.configuration:
            return

        desired_cylinders = self._get_cylinder_count()
        current_cylinders = [cylinder.cylinder_number for cylinder in self.compression]

        for cylinder in self.compression.filtered(
                lambda x: x.cylinder_number > desired_cylinders
        ):
            self.compression -= cylinder

        for i in range(1, desired_cylinders + 1):
            if i not in current_cylinders:
                new_cylinder = self.compression.new(
                    {
                        "cylinder_number": i,
                        "compression_psi": 0,
                    }
                )
                self.compression += new_cylinder

    def _create_default_images(self, motor_record: Self) -> None:
        image_names = constants.MOTOR_IMAGE_NAME_AND_ORDER
        for name in image_names:
            self.env["motor.image"].create(
                {
                    "motor": motor_record.id,
                    "name": name,
                }
            )

    def _update_stage(self) -> None:
        stages_with_required_fields = {
            "basic_testing": [
                "motor_number",
                "manufacturer",
                "stroke",
                "configuration",
                "color",
            ],
            "extended_testing": [
                # "engine_ecu_hours",
                # "shaft_length",
                # "compression_numbers",
                # "fuel_pump_status",
                # "trim_tilt_unit_status",
                # "lower_unit_fluid_condition",
                # "lower_unit_pressure_status",
            ],
            "finalization": [
                # "lower_unit_gear_engages_when_removed",
            ],
        }

        for stage, stage_fields in stages_with_required_fields.items():
            if all(getattr(self, f, None) for f in stage_fields):
                self.stage = stage
            else:
                break
