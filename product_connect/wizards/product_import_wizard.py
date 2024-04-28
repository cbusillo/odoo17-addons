import odoo
from odoo.exceptions import UserError


class ProductImportWizard(odoo.models.TransientModel):
    _name = "product.import.wizard"
    _description = "Product Import Wizard"

    total_cost = odoo.fields.Float(required=True)

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


class ProductImportImageWizard(odoo.models.TransientModel):
    _name = 'product.import.image.wizard'
    _description = 'Product Import Photo Wizard'

    product = odoo.fields.Many2one('product.import', string='Product')
    barcode = odoo.fields.Char(string='Product Barcode')
    default_code = odoo.fields.Char(string='Product SKU', related='product.default_code', readonly=True)
    name = odoo.fields.Char(string='Product Name', related='product.name', readonly=True)
    images = odoo.fields.One2many(related='product.images')

    @odoo.api.onchange('barcode')
    def _onchange_product_barcode(self) -> None:
        if self.barcode:
            product = self.env['product.import'].search([('default_code', '=', self.barcode)], limit=1)
            if product:
                self.product = product
                self._ensure_image_placeholders(product.id)
            else:
                # noinspection PyProtectedMember
                raise UserError(odoo._('No product found with the given barcode.'))

    @odoo.api.model
    def default_get(self, fields) -> dict[str, str]:
        res = super(ProductImportImageWizard, self).default_get(fields)
        product_id = res.get('product')
        if product_id:
            self._ensure_image_placeholders(product_id)
        return res

    def _ensure_image_placeholders(self, product_id) -> None:
        product = self.env['product.import'].browse(product_id)
        existing_images_count = len(product.images)
        placeholders_needed = 20 - existing_images_count
        if placeholders_needed > 0:
            new_images = [{'product': product.id, 'index': i + existing_images_count} for i in
                          range(placeholders_needed)]
            self.env['product.import.image'].create(new_images)

    def action_next_product(self) -> dict[str, str]:
        self.ensure_one()
        if not self.product:
            product = self.env['product.import'].search([], order='id', limit=1)
        else:
            product = self.env['product.import'].search([('id', '>', self.product.id)], order='id', limit=1)
            if not product:
                product = self.env['product.import'].search([], order='id', limit=1)
        self.product = product
        self._ensure_image_placeholders(product.id)
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
        self._ensure_image_placeholders(product.id)
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'product.import.image.wizard',
            'res_id': self.id,
            'target': 'new',
        }

    def action_edit_next(self) -> dict[str, str]:
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'product.import.image.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_done(self) -> dict[str, str]:
        self.ensure_one()
        # Assuming image data is handled by the client and needs to be saved:
        self.product.images.unlink()  # Clear existing placeholders or unused images
        for wizard_image in self.images:
            if wizard_image.image_1920:  # Ensure there's actual image data
                wizard_image.create({
                    'product': self.product.id,
                    'image_1920': wizard_image.image_1920,
                    'index': wizard_image.index
                })
        return {
            'type': 'ir.actions.act_window_close',
        }
