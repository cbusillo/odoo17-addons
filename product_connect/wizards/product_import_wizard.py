import odoo
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ProductImportWizard(models.TransientModel):
    _name = "product.import.wizard"
    _description = "Product Import Wizard"

    total_cost = fields.Float(required=True)

    def apply_cost(self) -> dict[str, str]:
        products = self.env["product.import"].search([])
        total_price = sum(record.list_price * record.qty_available for record in products)

        for product in products:
            cost_proportion = (product.list_price * product.qty_available) / total_price if total_price else 0
            product.standard_price = (
                (cost_proportion * self.total_cost) / product.qty_available if product.qty_available else 0
            )
        return {
            "type": "ir.actions.act_window",
            "res_model": "product.import",
            "view_mode": "tree",
            "target": "current",
        }


class ProductImportImageWizard(models.TransientModel):
    _name = "product.import.image.wizard"
    _description = "Product Import Photo Wizard"

    product = fields.Many2one("product.import")
    barcode = fields.Char(size=20)
    default_code = fields.Char(string="SKU", related="product.default_code", readonly=True)
    name = fields.Char(related="product.name", readonly=True)
    images = fields.One2many(related="product.images")

    # noinspection PyShadowingNames
    @api.model
    def default_get(self, fields: list[str]) -> dict[str, str]:
        res = super(ProductImportImageWizard, self).default_get(fields)
        product = res.get("product")
        if product:
            self._ensure_image_placeholders(product)
        return res

    @api.onchange("barcode")
    def _onchange_product_barcode(self) -> None:
        self._lookup()

    @api.onchange("product")
    def _onchange_product(self) -> None:
        self._ensure_image_placeholders(self.product)
        existing_images = self.product.images.filtered(lambda i: i.index is not None)
        self.update({"images": [(6, 0, existing_images.ids)]})

    def _ensure_image_placeholders(self, product: "odoo.model.product_import") -> None:
        if not product:
            return

        current_indexes = {image.index for image in product.images if image.index is not None}
        max_index = 19
        missing_indexes = set(range(max_index + 1)) - current_indexes

        new_images_data = [{"product": product.id, "index": index} for index in missing_indexes]
        self.images.create(new_images_data)

    @api.onchange("images")
    def _save_images_onchange(self) -> None:
        if not self.product:
            return None

        for image in self.images:
            image_id = image._origin.id
            if image_id:  # Ensure we only update existing records
                self.env["product.import.image"].browse(image_id).write(
                    {
                        "image_1920": image.image_1920,
                        "index": image.index,
                    }
                )

    def action_next_product(self) -> dict[str, str]:
        return self._navigate_product("next")

    def action_previous_product(self) -> dict[str, str]:
        return self._navigate_product("previous")

    def _navigate_product(self, direction: str) -> dict[str, str]:
        self._exit_product()

        order = "id" if direction == "next" else "id desc"
        comparison = ">" if direction == "next" else "<"

        current_product_id = self.product.id if self.product else None
        product = (
            self.env["product.import"].search([("id", comparison, current_product_id)], order=order, limit=1)
            if current_product_id
            else self.env["product.import"].search([], order=order, limit=1)
        )

        if not product or (current_product_id and product.id == current_product_id):
            product = self.env["product.import"].search([], order=order, limit=1)

        if product:
            self.product = product
            self._ensure_image_placeholders(product)

        return {
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_model": "product.import.image.wizard",
            "res_id": self.id,
            "target": "new",
        }

    def action_done(self) -> dict[str, str]:
        self._exit_product()
        return {
            "type": "ir.actions.client",
            "tag": "reload_context",
        }

    def _exit_product(self) -> None:
        self.ensure_one()
        self.barcode = None
        unused_images = self.images.filtered(lambda r: not r.image_1920)
        if unused_images:
            unused_images.unlink()

    def _lookup(self) -> None:
        self.ensure_one()
        barcode = self.barcode
        self._exit_product()
        if not barcode:
            return None
        product = self.env["product.import"].search([("default_code", "=", barcode)], limit=1)
        if not product:
            # noinspection PyProtectedMember
            raise UserError(_("No product found with the given barcode."))

        self.product = product
        self._ensure_image_placeholders(product)
