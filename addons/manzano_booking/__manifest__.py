{
    "name": "Manzano Booking Core",
    "version": "1.0.0",
    "summary": "Atomic booking confirmation flow for Odoo Manzano",
    "depends": ["sale", "mail"],
    "data": [
        "security/ir.model.access.csv",
        "views/sale_order_views.xml",
    ],
    "installable": True,
    "application": False,
}
