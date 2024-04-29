import logging

_logger = logging.getLogger(__name__)


def migrate(cr, _version) -> None:
    _logger.info(f"Running pre-migration script: {__name__}")

    # noinspection SqlWithoutWhere
    cr.execute("DELETE FROM product_import_image")

    deleted_count = cr.rowcount
    _logger.info("Deleted %d records from product_import_image table", deleted_count)

    _logger.info("Pre-migration script completed")
