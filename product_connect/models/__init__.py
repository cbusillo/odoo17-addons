import importlib

modules = [
    'motor',
    'motor_part',
    'motor_product',
    'motor_test',
    'printnode_interface',
    'product_color',
    'product_import',
    'product_manufacturer',
    'product_product',
    'product_template',
    'res_users',
    'shopify_sync'
]

__all__ = modules

globals().update({
    module: importlib.import_module('.' + module, package=__name__)
    for module in modules
})
