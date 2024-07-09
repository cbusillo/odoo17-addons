import logging

from odoo.upgrade import util

_logger = logging.getLogger(__name__)


# noinspection SqlResolve
def migrate(cr, version) -> None:
    _logger.info("Post-migration: set default values for manufacturer and condition")
    env = util.env(cr)

    motor_products = env["motor.product"].search([])
    for product in motor_products:
        if not product.manufacturer:
            product.manufacturer = product.motor.manufacturer
        if not product.condition:
            product.condition = env.ref("product_connect.product_condition_used")

    _logger.info("Post-migration: set default values for manufacturer and condition")
