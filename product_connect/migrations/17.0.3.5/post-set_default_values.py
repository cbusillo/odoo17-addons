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

        product.part_type_name = product.part_type.name
        product._compute_name()

    product_imports = env["product.import"].search([])
    for product in product_imports:
        product.part_type_name = product.part_type.name

    product_templates = env["product.template"].search([])
    for product in product_templates:
        product.part_type_name = product.part_type.name

    _logger.info("Post-migration: set default values for manufacturer and condition")
