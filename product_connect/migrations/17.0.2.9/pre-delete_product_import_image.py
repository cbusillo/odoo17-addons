import logging

from odoo.upgrade.util import rename_field

_logger = logging.getLogger(__name__)


def migrate(cr, version) -> None:
    _logger.info("Running post-migration script.")

    cr.execute("DELETE FROM product_import_image WHERE product_id IS NULL")
    rename_field(cr, "product.import.image", "product_id", "product")

    cr.connection.commit()
    _logger.info("Removed records with NULL 'product' values.")
