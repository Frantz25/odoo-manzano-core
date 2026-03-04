{
    "name": "Manzano Catalog",
    "version": "1.0.0",
    "summary": "Operational catalog with idempotent sync",
    "author": "Manzano",
    "license": "LGPL-3",
    "depends": ["base", "mail"],
    "data": [
        "security/ir.model.access.csv",
        "views/catalog_item_views.xml",
        "views/catalog_sync_wizard_views.xml",
        "views/catalog_menus.xml",
    ],

    "installable": True,
    "application": False,
}
