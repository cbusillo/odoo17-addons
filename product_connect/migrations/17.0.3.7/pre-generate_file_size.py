import logging

from odoo.sql_db import Cursor
from odoo.upgrade import util

_logger = logging.getLogger(__name__)


def migrate(cr: Cursor, version: str) -> None:
    util.create_column(cr, "product_image", "file_size", "integer")
    env = util.env(cr)

    product_images = env["product.image"].search([])
    _logger.info(f"Pre-migration: Generate {product_images.search_count([])} file size fields")

    current_count = 0
    for image in product_images:
        image.file_size = len(image.image_1920) if image.image_1920 else 0
        if current_count % 1000 == 0:
            # env.cr.commit()
            _logger.info(f"Pre-migration: Updated {current_count} image file sizes")
        current_count += 1

    _logger.info(f"Pre-migration: Renamed {current_count} product fields")
