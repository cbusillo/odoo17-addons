import importlib

modules = [
    "test_shopify_sync",
]

__all__ = modules

globals().update({module: importlib.import_module("." + module, package=__name__) for module in modules})
