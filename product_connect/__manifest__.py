# -*- coding: utf-8 -*-
{
    "name": "Product Connect Module",
    "version": "17.0.1.3",
    "category": "Industries",
    "author": "Chris Busillo",
    "company": "Shiny Computers",
    "website": "https://www.shinycomputers.com",
    "depends": [
        "base",
        "product",
        "web",
        "website_sale",
        "base_automation",
        "stock",
    ],
    "description": "Module to scrape websites for model data.",
    "data": [
        "data/res_config_data.xml",
        "security/ir.model.access.csv",
        "views/printnode_interface_views.xml",
        "views/shopify_sync_views.xml",
        "views/product_import_views.xml",
        "views/product_import_wizard.xml",
        "views/product_scraper_wizard.xml",  # Needs to be before product_template_views.xml to allow button for action
        "views/product_product_views.xml",
        "views/product_scraper_views.xml",
        "views/product_template_views.xml",
        "views/product_manufacturer_views.xml",
        "views/res_config_settings_views.xml",
        "views/product_import_motor_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "product_connect/static/src/js/file_drop_widget.js",
            "product_connect/static/src/css/file_drop_widget.css",
            "product_connect/static/src/js/search_mpn_online_widget.js",
        ],
    },
    "installable": True,
    "application": True,
    "license": "LGPL-3",
}
