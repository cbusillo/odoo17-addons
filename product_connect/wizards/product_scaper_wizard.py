from odoo import models


class ProductScraperWizard(models.TransientModel):
    _name = "product.scraper.wizard"
    _description = "Product Scraper Wizard"

    def action_scrape_website(self):
        self.env["product.scraper"].scrape_website()
        return {"type": "ir.actions.act_window_close"}

    def action_sync_with_shopify(self):
        self.env["shopify.sync"].sync_with_shopify()
        return {"type": "ir.actions.act_window_close"}
