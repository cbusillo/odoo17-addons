import logging

_logger = logging.getLogger(__name__)


def migrate(cr, _version) -> None:
    _logger.info(f"Running pre-migration script: {__name__}")

    cr.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='product_import_image' AND column_name='product'
    """)
    result = cr.fetchone()

    if result:
        # noinspection SqlResolve
        cr.execute("ALTER TABLE product_import_image RENAME COLUMN product to product_id")

    cr.execute("DELETE FROM product_import_image WHERE product_id IS NULL")

    deleted_count = cr.rowcount
    _logger.info("Deleted %d records from product_import_image table", deleted_count)

    _logger.info("Pre-migration script completed")
