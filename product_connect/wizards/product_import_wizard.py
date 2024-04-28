from odoo.exceptions import UserError

from odoo import _, api, fields, models


class ProductImportWizard(models.TransientModel):
    _name = "product.import.wizard"
    _description = "Product Import Wizard"

    total_cost = fields.Float(required=True)

    def apply_cost(self) -> dict[str, str]:
        products = self.env["product.import"].search([])
        total_price = sum(record.price * record.quantity for record in products)

        for product in products:
            cost_proportion = (
                (product.price * product.quantity) / total_price if total_price else 0
            )
            product.cost = (
                (cost_proportion * self.total_cost) / product.quantity
                if product.quantity
                else 0
            )
        return {
            "type": "ir.actions.act_window",
            "res_model": "product.import",
            "view_mode": "tree",
            "target": "current",
        }


class ProductImportImageWizard(models.TransientModel):
    _name = 'product.import.image.wizard'
    _description = 'Product Import Photo Wizard'

    product = fields.Many2one('product.import', string='Product')
    barcode = fields.Char(string='Product Barcode')
    default_code = fields.Char(string='Product SKU', related='product.default_code', readonly=True)
    name = fields.Char(string='Product Name', related='product.name', readonly=True)
    images = fields.One2many(related='product.images')

    @api.onchange('barcode')
    def _onchange_product_barcode(self) -> None:
        if self.barcode:
            product = self.env['product.import'].search([('default_code', '=', self.barcode)], limit=1)
            if product:
                self.product = product
            else:
                raise UserError(_('No product found with the given barcode.'))

    def action_next_product(self) -> dict[str, str]:
        self.ensure_one()
        if not self.product:
            product = self.env['product.import'].search([], order='id', limit=1)
        else:
            product = self.env['product.import'].search([('id', '>', self.product.id)], order='id', limit=1)
            if not product:
                product = self.env['product.import'].search([], order='id', limit=1)
        self.product = product
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'product.import.image.wizard',
            'res_id': self.id,
            'target': 'new',
        }

    def action_previous_product(self) -> dict[str, str]:
        self.ensure_one()
        if not self.product:
            product = self.env['product.import'].search([], order='id desc', limit=1)
        else:
            product = self.env['product.import'].search([('id', '<', self.product.id)], order='id desc', limit=1)
            if not product:
                product = self.env['product.import'].search([], order='id desc', limit=1)
        self.product = product
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'product.import.image.wizard',
            'res_id': self.id,
            'target': 'new',
        }
