from odoo import models, fields


class ProductColorTag(models.Model):
    _name = "product.color.tag"
    _description = "Product Color Tag"

    name = fields.Char(required=True)


class ProductColor(models.Model):
    _name = "product.color"
    _description = "Product Color"

    name = fields.Char(required=True)
    color_code = fields.Char(help="The HEX color code, e.g., #FFFFFF for white.")
    applicable_tags_ids = fields.Many2many("product.color.tag", string="Applicable For")
