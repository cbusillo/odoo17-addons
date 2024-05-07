from odoo import fields, models
from ..utils.constants import YES_NO_SELECTION


class MotorTestSection(models.Model):
    _name = "motor.test.section"
    _description = "Motor Test Section"
    _order = "sequence, id"

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    templates = fields.One2many("motor.test.template", "section")
    tests = fields.One2many("motor.test", "section")
    motor = fields.Many2one("motor", ondelete="restrict")


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
    default_value = fields.Char()
    conditions = fields.One2many(
        "motor.test.template.condition",
        "template",
    )
    conditional_tests = fields.One2many(
        "motor.test.template.condition",
        "conditional_test",
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
    conditional_test = fields.Many2one("motor.test.template", ondelete="cascade")
    condition_value = fields.Char(required=True)
    action_type = fields.Selection(
        [
            ("show", "Show Test"),
            ("hide", "Hide Test"),
        ],
    )


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

    name = fields.Char(related="template.name")
    motor = fields.Many2one("motor", ondelete="restrict", required=True)
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
    default_value = fields.Char(related="template.default_value")
    is_applicable = fields.Boolean(default=True)

    conditions = fields.One2many(
        "motor.test.template.condition",
        related="template.conditions",
    )
    conditional_tests = fields.One2many(
        "motor.test.template.condition",
        related="template.conditional_tests",
    )
