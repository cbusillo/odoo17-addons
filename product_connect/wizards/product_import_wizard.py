from odoo import fields, models


class ProductImportWizard(models.TransientModel):
    _name = "product.import.wizard"
    _description = "Product Import Wizard"

    total_cost = fields.Float(required=True)

    def apply_cost(self):
        products = self.env["product.import"].search([])
        total_price = sum(record.price * record.quantity for record in products)

        for product in products:
            cost_proportion = (product.price * product.quantity) / total_price if total_price else 0
            product.cost = (cost_proportion * self.total_cost) / product.quantity if product.quantity else 0
        return {
            "type": "ir.actions.act_window",
            "res_model": "product.import",
            "view_mode": "tree",
            "target": "current",
        }
