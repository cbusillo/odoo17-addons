from odoo import models, fields


class ProductImportMotor(models.Model):
    _name = "product.import.motor"
    _description = "Product Import Motor"

    year = fields.Char()
    manufacturer = fields.Many2one("product.manufacturer", index=True)
    model_number = fields.Char()
    serial_number = fields.Char()
    shaft_length = fields.Selection(
        [
            ("15", "15(S)"),
            ("20", "20(L)"),
            ("25", "25(XL)"),
            ("30", "30(XXL)"),
        ],
    )
    rotation = fields.Selection(
        [
            ("standard", "Standard(RH)"),
            ("counter", "Counter(LH)"),
        ]
    )
    horsepower = fields.Char()
    cost = fields.Float()
    image_left = fields.Image(max_width=1920, max_height=1920)
    image_right = fields.Image(max_width=1920, max_height=1920)
    image_lower = fields.Image(max_width=1920, max_height=1920)
    image_trim = fields.Image(max_width=1920, max_height=1920)
    image_serial = fields.Image(max_width=1920, max_height=1920)
