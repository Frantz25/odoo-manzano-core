{
    "name": "Manzano Catalog Integration",
    "version": "1.0.0",
    "summary": "Catalog to sales/booking integration",
    "author": "Manzano",
    "license": "LGPL-3",
    "depends": ["sale", "manzano_catalog", "manzano_booking"],
    "data": [
        "security/ir.model.access.csv",
        "views/sale_order_line_views.xml",
    ],
    "installable": True,
    "application": False,
}
