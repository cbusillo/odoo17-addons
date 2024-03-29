import re
from odoo import models, fields, api


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

    @api.depends("name")
    def _compute_name_normalized(self) -> None:
        for record in self:
            record.name_normalized = self.normalize_name(record.name)

    @staticmethod
    def normalize_name(name: str) -> str:
        return re.sub(r"\W+", "", name).lower() if name else ""

    def create(self, vals_list: dict | list[dict]):
        if not isinstance(vals_list, list):
            vals_list = [vals_list]
        for vals in vals_list:
            name_normalized = self.normalize_name(vals.get("name"))
            existing_manufacturer = self.search(
                [("name_normalized", "=", name_normalized)]
            )
            if existing_manufacturer:
                return existing_manufacturer
            else:
                return super().create(vals)
