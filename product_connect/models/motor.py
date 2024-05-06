import base64
import re
from io import BytesIO
from typing import Any, Self

import qrcode  # type: ignore
from odoo.exceptions import ValidationError

from odoo import _, api, fields, models
from ..mixins.label import LabelMixin
from ..utils import constants


class MotorCompression(models.Model):
    _name = "motor.compression"
    _description = "Motor Compression Data"
    _order = "cylinder_number"

    motor = fields.Many2one("motor", ondelete="restrict")
    cylinder_number = fields.Integer()
    compression_psi = fields.Integer("Compression PSI")
    compression_image = fields.Binary()


class MotorImage(models.Model):
    _name = "motor.image"
    _inherit = ["image.mixin"]
    _description = "Motor Images"

    motor = fields.Many2one("motor", ondelete="restrict")
    name = fields.Char()
    image_data = fields.Binary()


class Motor(models.Model, LabelMixin):
    _name = "motor"
    _description = "Motor Information"
    _order = "id desc"

    # Basic Info
    name = fields.Char(compute="_compute_name", readonly=True, store=True)
    active = fields.Boolean(default=True)
    motor_number = fields.Char()
    technician = fields.Many2one(
        "res.users", string="Tech Name",
        domain="[('is_technician', '=', True),('active', 'in', [True, False])]",
        ondelete="restrict",
    )
    manufacturer = fields.Many2one("product.manufacturer", domain="[('is_engine_manufacturer', '=', True)]")
    horsepower = fields.Float(digits=(3, 1), string="HP")
    motor_stroke = fields.Selection(constants.MOTOR_STROKE_SELECTION)
    motor_configuration = fields.Selection(constants.MOTOR_CONFIGURATION_SELECTION)
    model = fields.Char()
    serial_number = fields.Char()

    @api.model
    def _get_years(self) -> list[tuple[str, str]]:
        return [
            (str(year), str(year))
            for year in range(fields.Date.today().year + 1, 1960, -1)
        ]

    year = fields.Selection(_get_years, string="Model Year")
    color = fields.Many2one("product.color", domain="[('applicable_tags.name', '=', 'Motors')]")
    cost = fields.Float()

    is_tag_readable = fields.Selection(constants.YES_NO_SELECTION, default=constants.YES)
    notes = fields.Text()
    images = fields.One2many("motor.image", "motor")
    parts = fields.One2many("motor.part", "motor")
    tests = fields.One2many("motor.test", "motor")
    test_sections = fields.One2many("motor.test.section", "motor")
    basic_tests = fields.One2many("motor.test", "motor", domain=[("template.stage", "=", "basic")])
    extended_tests = fields.One2many("motor.test", "motor", domain=[("template.stage", "=", "extended")])

    compression = fields.One2many("motor.compression", "motor")
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
            record._create_motor_products()
        return result

    def unlink(self) -> None:
        if not self.env.user.has_group("base.group_system"):
            raise ValidationError("Cannot delete a user, please archive.")

        return super().unlink()

    @api.depends(
        "motor_number", "manufacturer", "model", "year", "serial_number", "horsepower"
    )
    def _compute_name(self) -> None:
        for record in self:
            serial_number = (
                f" - {record.serial_number}" if record.serial_number else None
            )

            name_parts = [
                record.motor_number,
                record.year,
                record.manufacturer.name,
                record.get_horsepower_formatted(),
                record.model,
                serial_number,
            ]
            name = " ".join(part for part in name_parts if part)

            if name:
                record.name = name

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
        return (
            f" {int(self.horsepower)}HP"
            if self.horsepower and self.horsepower.is_integer()
            else f" {self.horsepower}HP"
            if self.horsepower
            else ""
        )

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
            if product_template.motor_stroke and product_template.motor_stroke != self.motor_stroke:
                continue
            if product_template.motor_configuration and product_template.motor_configuration != self.motor_configuration:
                continue
            if product_template.manufacturer and product_template.manufacturer != self.manufacturer:
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
        match = re.search(r"\d+", self.motor_configuration)
        if match:
            return int(match.group())
        return 0

    @api.onchange("motor_configuration")
    def _onchange_motor_configuration(self) -> None:
        if not self.motor_configuration:
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
                "motor_stroke",
                "motor_configuration",
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
