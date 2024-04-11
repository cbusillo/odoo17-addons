import re
from typing import Any, Self

from odoo import _, models, fields, api
from odoo.exceptions import ValidationError

YES = "yes"
NO = "no"

YES_NO_SELECTION = [
    (YES, "Yes"),
    (NO, "No"),
]


class MotorTestSection(models.Model):
    _name = "motor.test.section"
    _description = "Motor Test Section"
    _order = "sequence, id"

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    templates = fields.One2many("motor.test.template", "section")
    tests = fields.One2many("motor.test", "section")
    motor = fields.Many2one("motor")


class MotorTestTemplate(models.Model):
    _name = "motor.test.template"
    _description = "Motor Test Template"
    _order = "sequence, id"

    name = fields.Char("Test Name", required=True)
    result_type = fields.Selection(
        [
            ("yes_no", "Yes/No"),
            ("numeric", "Numeric"),
            ("text", "Text"),
            ("selection", "Selection"),
            ("file", "File Upload"),
        ],
        string="Test Type",
        required=True,
    )
    selection_options = fields.Many2many("motor.test.selection")
    conditional_tests = fields.Many2many(
        "motor.test.template",
        "motor_test_template_conditional_rel",
        "test_id",
        "conditional_test_id",
    )
    conditions = fields.One2many(
        "motor.test.template.condition",
        "template",
    )
    stage = fields.Selection(
        [
            ("basic", "Basic Testing"),
            ("extended", "Extended Testing"),
        ],
        required=True,
    )
    section = fields.Many2one("motor.test.section")

    sequence = fields.Integer(default=10)


class MotorTestTemplateCondition(models.Model):
    _name = "motor.test.template.condition"
    _description = "Motor Test Template Condition"

    template = fields.Many2one("motor.test.template", ondelete="cascade")
    condition_value = fields.Char(required=True)
    action_type = fields.Selection(
        [
            ("show", "Show Test"),
            ("hide", "Hide Test"),
        ],
    )
    conditional_test = fields.Many2one("motor.test.template", ondelete="cascade")


class MotorTestSelection(models.Model):
    _name = "motor.test.selection"
    _description = "Motor Test Selection"

    name = fields.Char(required=True)
    value = fields.Char(required=True)
    templates = fields.Many2many("motor.test.template", ondelete="cascade")


class MotorTest(models.Model):
    _name = "motor.test"
    _description = "Motor Test Instance"
    _order = "section_sequence, sequence, id"

    name = fields.Text(related="template.name")
    motor = fields.Many2one("motor", ondelete="cascade", required=True)
    template = fields.Many2one(
        "motor.test.template", string="Test Template", ondelete="restrict"
    )
    sequence = fields.Integer(
        string="Test Sequence", related="template.sequence", index=True, store=True
    )
    result_type = fields.Selection(related="template.result_type")
    section = fields.Many2one(related="template.section")
    section_sequence = fields.Integer(
        string="Section Sequence", related="section.sequence", index=True, store=True
    )

    yes_no_result = fields.Selection(YES_NO_SELECTION)
    selection_options = fields.Many2many(related="template.selection_options")

    selection_result = fields.Many2one(
        "motor.test.selection",
        domain="[('id', 'in', selection_options)]",
    )

    numeric_result = fields.Float()
    text_result = fields.Text()
    file_result = fields.Binary()
    is_applicable = fields.Boolean(default=True)
    conditional_tests = fields.Many2many(
        "motor.test.template", related="template.conditional_tests"
    )


class MotorPartTemplate(models.Model):
    _name = "motor.part.template"
    _description = "Motor Parts Available"
    _order = "sequence, id"

    name = fields.Char(required=True)
    hidden_tests = fields.Many2many("motor.test.template", string="Hidden Tests")
    hide_compression_page = fields.Boolean()
    sequence = fields.Integer(default=10)


class MotorPart(models.Model):
    _name = "motor.part"
    _description = "Motor Parts"
    _order = "sequence, id"

    motor = fields.Many2one(comodel_name="motor", required=True, ondelete="cascade")
    template = fields.Many2one(
        comodel_name="motor.part.template",
        ondelete="cascade",
    )
    name = fields.Char(related="template.name")
    sequence = fields.Integer(related="template.sequence", index=True, store=True)
    hidden_tests = fields.Many2many(
        "motor.test.template", related="template.hidden_tests", readonly=False
    )
    missing = fields.Boolean(default=False)


class MotorCompression(models.Model):
    _name = "motor.compression"
    _description = "Motor Compression Data"

    motor = fields.Many2one("motor", ondelete="cascade")
    cylinder_number = fields.Integer()
    compression_psi = fields.Float("Compression PSI")
    compression_image = fields.Binary()


class MotorImage(models.Model):
    _name = "motor.image"
    _description = "Motor Images"

    motor = fields.Many2one("motor", ondelete="cascade")
    name = fields.Char()
    image_data = fields.Image("Image", max_width=1920, max_height=1920)


class Motor(models.Model):
    _name = "motor"
    _description = "Motor Information"

    # Basic Info
    motor_number = fields.Char()
    manufacturer = fields.Many2one("product.manufacturer")
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

    @api.model
    def _get_years(self) -> list[tuple[str, str]]:
        return [
            (str(year), str(year))
            for year in range(fields.Date.today().year + 1, 1960, -1)
        ]

    year = fields.Selection(_get_years, string="Model Year")
    color = fields.Many2one(
        "product.color",
        domain="[('applicable_tags.name', '=', 'Motors')]",
    )
    cost = fields.Float()

    tag_readable = fields.Selection(YES_NO_SELECTION, default=YES)
    images = fields.One2many("motor.image", "motor")
    parts = fields.One2many("motor.part", "motor")
    tests = fields.One2many("motor.test", "motor")
    test_sections = fields.One2many("motor.test.section", "motor")
    basic_tests = fields.One2many(
        "motor.test", "motor", domain=[("template.stage", "=", "basic")]
    )
    extended_tests = fields.One2many(
        "motor.test", "motor", domain=[("template.stage", "=", "extended")]
    )

    # Basic Testing
    compression = fields.One2many("motor.compression", "motor")
    hide_compression_page = fields.Boolean(
        compute="_compute_hide_compression_page",
        store=True,
    )

    @api.depends("parts.missing", "parts.template.hide_compression_page")
    def _compute_hide_compression_page(self) -> None:
        for motor in self:
            hide_parts = motor.parts.filtered(
                lambda p: p.missing and p.template.hide_compression_page
            )
            motor.hide_compression_page = bool(hide_parts)

    # Extended Testing
    # Finalization
    stage = fields.Selection(
        [
            ("basic_info", "Basic Info"),
            ("images", "Images"),
            ("parts", "Parts"),
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
                record.horsepower and not (0.0 <= record.horsepower <= 600.0)
            ):
                raise ValidationError(_("Horsepower must be between 1 and 600."))

    @staticmethod
    def _sanitize_vals(vals: dict[str:Any]) -> dict[str, Any]:
        if "year" in vals and vals["year"]:
            vals["year"] = "".join(char for char in vals["year"] if char.isdigit())
        if "model" in vals and vals["model"]:
            vals["model"] = vals["model"].upper()
        if "serial_number" in vals and vals["serial_number"]:
            vals["serial_number"] = vals["serial_number"].upper()
        return vals

    @api.model_create_multi
    def create(self, vals_list: list[dict]) -> Self:
        vals_list = [self._sanitize_vals(vals) for vals in vals_list]

        records = super().create(vals_list)
        for record in records:
            record.motor_number = f"M-{record.id}"
            record._create_default_images(record)
            if record.motor_configuration:
                record._create_compression_records()

            record._create_motor_parts()
            record._create_motor_tests()

        return records

    def write(self, vals) -> Self:
        if self.env.context.get("_stage_updating"):
            return super().write(vals)
        vals = self._sanitize_vals(vals)

        result = super().write(vals)
        if "motor_configuration" in vals:
            self._create_compression_records()
        for record in self.with_context(_stage_updating=True):
            record._update_stage()
        return result

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

    def _get_cylinder_count(self) -> int:
        match = re.search(r"\d+", self.motor_configuration)
        if match:
            return int(match.group())
        return 0

    def _create_compression_records(self) -> None:
        existing_compressions = {c.cylinder_number: c for c in self.compression}
        cylinder_count = self._get_cylinder_count()
        compression_vals = []
        for i in range(1, cylinder_count + 1):
            if i not in existing_compressions:
                compression_vals.append(
                    {
                        "motor": self.id,
                        "cylinder_number": i,
                        "compression_psi": 0.0,
                    }
                )
        if compression_vals:
            self.env["motor.compression"].create(compression_vals)

    def _create_default_images(self, motor_record: Self) -> None:
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
