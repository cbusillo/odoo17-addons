import logging

from odoo.sql_db import Cursor
from odoo.upgrade import util


def migrate(cr: Cursor, version: str) -> None:
    _logger = logging.getLogger(__name__)
    _logger.info("Pre-migration: Removing old Shopify settings")

    env = util.orm.env(cr)
    env["ir.config_parameter"].sudo().search([("key", "ilike", "shopify%")]).unlink()

    _logger.info("Pre-migration: Removed old Shopify settings")
