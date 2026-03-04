{
    "name": "Manzano Booking Core",
    "version": "1.0.1",
    "summary": "Atomic booking confirmation flow for Odoo Manzano",
    "author": "Manzano",
    "license": "LGPL-3",
    "depends": ["sale", "mail"],
    "data": [
        "security/ir.model.access.csv",
        "views/sale_order_views.xml",
        "data/cron.xml",
    ],
    "installable": True,
    "application": False,
}
