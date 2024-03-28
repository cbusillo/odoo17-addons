import re
from typing import Self

from odoo import _, models, fields, api
from odoo.exceptions import ValidationError


class ProductMotorCompression(models.Model):
    _name = "product.motor.compression"
    _description = "Motor Compression Data"

    motor_id = fields.Many2one("product.motor", ondelete="cascade")
    cylinder_number = fields.Integer()
    compression_psi = fields.Float("Compression PSI")
    compression_image = fields.Binary()


class ProductMotorImage(models.Model):
    _name = "product.motor.image"
    _description = "Motor Images"

    motor_id = fields.Many2one("product.motor", ondelete="cascade")
    name = fields.Char()
    image = fields.Image("Image", max_width=1920, max_height=1920)


class ProductMotor(models.Model):
    _name = "product.motor"
    _description = "Motor Information"

    YES = "yes"
    NO = "no"

    YES_NO_SELECTION = [
        (YES, "Yes"),
        (NO, "No"),
    ]

    # Basic Info
    motor_number = fields.Char()
    manufacturer_id = fields.Many2one("product.manufacturer")
    horsepower = fields.Float(digits=(3, 1))
    motor_stroke = fields.Selection(
        [
            ("2", "2 Stroke"),
            ("4", "4 Stroke"),
        ]
    )
    motor_configuration = fields.Selection(
        [
            ("i2", "Inline 2"),
            ("i3", "Inline 3"),
            ("i4", "Inline 4"),
            ("i6", "Inline 6"),
            ("v4", "V4"),
            ("v6", "V6"),
            ("v8", "V8"),
        ]
    )
    model = fields.Char()
    serial_number = fields.Char()
    year = fields.Integer(string="Model Year")
    color_id = fields.Many2one(
        "product.color",
        domain="[('applicable_tags_ids.name', '=', 'Motors')]",
    )
    cost = fields.Float()

    tag_readable = fields.Selection(YES_NO_SELECTION, default=YES)
    image_ids = fields.One2many("product.motor.image", "motor_id")

    # Basic Testing
    engine_ecu_hours = fields.Float("Engine / ECU Hours")
    lower_unit_rotation_check = fields.Selection(
        [
            ("not_tested", "Not Tested"),
            ("locked", "Locked up"),
            ("counter", "Counter Rotation"),
            ("standard", "Standard Rotation"),
        ],
    )
    shaft_length = fields.Selection(
        [
            ("15", '15" Short Shaft'),
            ("20", '20" Long Shaft'),
            ("25", '25" XL Shaft'),
            ("30", '30" XXL Shaft'),
        ],
    )
    motor_spins = fields.Selection(YES_NO_SELECTION)
    compression_numbers = fields.One2many("product.motor.compression", "motor_id")
    fuel_pump_is_electric = fields.Selection(YES_NO_SELECTION)
    fuel_pump_status = fields.Selection(
        [
            ("functional", "Functional"),
            ("not_functional", "Not Functional"),
            ("not_tested", "Not Tested"),
        ],
    )
    trim_tilt_unit_status = fields.Selection(
        [
            ("functional", "Functional"),
            ("bad_motor", "Bad Motor"),
            ("no_movement", "No Movement"),
            ("not_tested", "Not Tested"),
        ],
    )
    trim_tilt_unit_leaks = fields.Selection(YES_NO_SELECTION)
    lower_unit_gear_engages = fields.Selection(YES_NO_SELECTION)

    lower_unit_fluid_has_water = fields.Selection(YES_NO_SELECTION)
    lower_unit_fluid_has_metal = fields.Selection(YES_NO_SELECTION)

    lower_unit_holds_pressure = fields.Selection(YES_NO_SELECTION)
    drive_engages_reverse = fields.Selection(YES_NO_SELECTION)
    drive_engages_neutral = fields.Selection(YES_NO_SELECTION)
    drive_engages_forward = fields.Selection(YES_NO_SELECTION)
    engine_history_report_pdf = fields.Binary()

    # Extended Testing
    lower_unit_rotation_check_when_removed = fields.Selection(YES_NO_SELECTION)
    drive_shaft_seals_leaking = fields.Selection(YES_NO_SELECTION)
    prop_shaft_seals_leaking = fields.Selection(YES_NO_SELECTION)
    shift_shaft_seals_leaking = fields.Selection(YES_NO_SELECTION)
    # Finalization
    stage = fields.Selection(
        [
            ("basic_info", "Basic Info"),
            ("images", "Images"),
            ("basic_testing", "Basic Testing"),
            ("extended_testing", "Extended Testing"),
            ("finalization", "Finalization"),
        ],
        default="basic_info",
        required=True,
    )

    def get_horsepower_formatted(self) -> str:
        if self.horsepower.is_integer():
            return f"{int(self.horsepower)}HP"
        return f"{self.horsepower}HP"

    @api.constrains("horsepower")
    def _check_horsepower(self) -> None:
        for record in self:
            if not isinstance(record.horsepower, float) or (
                record.horsepower and not (0 <= record.horsepower <= 600)
            ):
                raise ValidationError(_("Horsepower must be between 1 and 600."))

    @api.constrains("year")
    def _check_year(self) -> None:
        for record in self:
            if record.year and not (1960 <= record.year <= fields.Date.today().year):
                raise ValidationError(
                    _("Year must be between 1950 and the current year.")
                )

    @api.model_create_multi
    def create(self, vals_list: list[dict]) -> Self:
        for vals in vals_list:
            if "year" in vals and vals["year"]:
                vals["year"] = "".join(filter(str.isdigit, vals["year"]))
            if "model" in vals and vals["model"]:
                vals["model"] = vals["model"].upper()
            if "serial_number" in vals and vals["serial_number"]:
                vals["serial_number"] = vals["serial_number"].upper()

        records = super().create(vals_list)
        for record in records:
            record.motor_number = f"M-{record.id}"
            record._create_default_images_for_motor(record)
            if record.motor_configuration:
                record._create_compression_records()
        return records

    def write(self, vals) -> Self:
        if self.env.context.get("_stage_updating"):
            return super().write(vals)
        if "year" in vals and vals["year"]:
            vals["year"] = "".join(filter(str.isdigit, vals["year"]))
        if "model" in vals and vals["model"]:
            vals["model"] = vals["model"].upper()
        if "serial_number" in vals and vals["serial_number"]:
            vals["serial_number"] = vals["serial_number"].upper()

        result = super().write(vals)
        if "motor_configuration" in vals:
            self._create_compression_records()
        for record in self.with_context(_stage_updating=True):
            record._update_stage()
        return result

    def _get_cylinder_count(self) -> int:
        match = re.search(r"\d+", self.motor_configuration)
        if match:
            return int(match.group())
        return 0

    def _create_compression_records(self) -> None:
        existing_compressions = {c.cylinder_number: c for c in self.compression_numbers}
        cylinder_count = self._get_cylinder_count()
        compression_vals = []
        for i in range(1, cylinder_count + 1):
            if i not in existing_compressions:
                compression_vals.append(
                    {
                        "motor_id": self.id,
                        "cylinder_number": i,
                        "compression_psi": 0.0,
                    }
                )
        if compression_vals:
            self.env["product.motor.compression"].create(compression_vals)

    def _create_default_images_for_motor(self, motor_record: Self) -> None:
        image_names = [
            "Port Side",
            "Starboard Side",
            "Port Mid Section",
            "Starboard Midsection",
            "Data Label",
            "Under Cowling - Port Side",
            "Under Cowling - Starboard Side",
            "Under Cowling - Front",
            "Under Cowling - Back",
        ]
        for name in image_names:
            self.env["product.motor.image"].create(
                {
                    "motor_id": motor_record.id,
                    "name": name,
                }
            )

    def _update_stage(self) -> None:
        stages_with_required_fields = {
            "basic_testing": [
                "motor_number",
                "motor_configuration",
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
