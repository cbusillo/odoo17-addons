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
                return None
            else:
                # noinspection PyProtectedMember
                raise UserError(odoo._('No product found with the given barcode.'))

    @odoo.api.model
    def default_get(self, fields) -> dict[str, str]:
        res = super(ProductImportImageWizard, self).default_get(fields)
        product_id = res.get('product_id')
        if product_id:
            self._ensure_image_placeholders(product_id)
        return res

    def _ensure_image_placeholders(self, product_id: int) -> None:
        product = self.env['product.import'].browse(product_id)
        if not product:
            return

        # Getting the highest current index, or -1 if no images exist
        if product.images:
            max_current_index = max(img.index for img in product.images if img.index is not None)
        else:
            max_current_index = -1

        # Define the range of indexes needed
        max_index = 19  # Assuming indexes from 0 to 19
        required_indexes = set(range(max_current_index + 1, max_index + 1))

        # Create placeholders only for required indexes beyond the max current index
        new_images_data = [{'product_id': product.id, 'index': idx} for idx in required_indexes]
        self.env['product.import.image'].create(new_images_data)

    @odoo.api.onchange('images')
    def _save_images_onchange(self) -> None:
        if self.product:
            for img in self.images:
                if img.id and img.image_1920:  # Ensures that there's existing data and it's an update
                    self.env['product.import.image'].browse(img.id).write({
                        'image_1920': img.image_1920,
                        'index': img.index
                    })
                elif not img.id and img.image_1920:  # Handle cases where it's a new image that needs to be saved
                    self.env['product.import.image'].create({
                        'product_id': self.product.id,
                        'image_1920': img.image_1920,
                        'index': img.index
                    })

    def action_next_product(self) -> dict[str, str]:
        self.ensure_one()
        current_product_id = self.product.id if self.product else None
        product = self.env['product.import'].search(
            [('id', '>', current_product_id)], order='id', limit=1) if current_product_id else self.env[
            'product.import'].search([], limit=1, order='id')

        if not product:
            product = self.env['product.import'].search(
                [], limit=1, order='id')  # Loop back to the first product if at the end

        if product and product.id != current_product_id:
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
        current_product_id = self.product.id if self.product else None
        product = self.env['product.import'].search(
            [('id', '<', current_product_id)], order='id desc', limit=1) if current_product_id else self.env[
            'product.import'].search([], limit=1, order='id desc')

        if not product:
            product = self.env['product.import'].search(
                [], limit=1, order='id desc')  # Loop back to the last product if at the beginning

        if product and product.id != current_product_id:
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
        self._exit_product()
        self.product = False
        self.default_code = False
        self.name = False
        self.images = [(5,)]

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'product.import.image.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_done(self) -> dict[str, str]:
        self.ensure_one()
        self._exit_product()
        return {
            'type': 'ir.actions.act_window_close',
        }

    def _exit_product(self) -> None:
        unused_images = self.images.filtered(lambda r: not r.image_1920)
        if unused_images:
            unused_images.unlink()
