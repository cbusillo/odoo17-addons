import re

from odoo import api, fields, models


class ProductManufacturer(models.Model):
    _name = "product.manufacturer"
    _description = "Product Manufacturer"
    _sql_constraints = [
        ("name_uniq", "unique (name)", "Product Manufacturer already exists !"),
        (
            "name_normalized_uniq",
            "unique (name_normalized)",
            "Product Manufacturer already exists !",
        ),
    ]

    name = fields.Char(required=True, index=True)
    name_normalized = fields.Char(
        compute="_compute_name_normalized", store=True, readonly=True
    )
    image_1920 = fields.Image(
        max_width=1920, max_height=1920, store=True, attachment=True, string="Image"
    )
    is_engine_manufacturer = fields.Boolean(
        "Is Engine Manufacturer",
        default=False,
        help="Indicates if the manufacturer produces engines.",
    )

    @api.depends("name")
    def _compute_name_normalized(self) -> None:
        for record in self:
            record.name_normalized = self.normalize_name(record.name)

    @staticmethod
    def normalize_name(name: str) -> str:
        return re.sub(r"\W+", "", name).lower() if name else ""
