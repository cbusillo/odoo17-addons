import logging

from odoo.upgrade import util

_logger = logging.getLogger(__name__)


# noinspection SqlResolve
def migrate(cr, version) -> None:
    _logger.info(
        "Pre-migration: Renaming model 'motor.compression' to 'motor_cylinder'"
    )
    util.rename_model(cr, "motor.compression", "motor.cylinder")

    _logger.info("Pre-migration: Renamed model 'motor.compression' to 'motor_cylinder'")
