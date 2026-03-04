{
    "name": "Manzano Catalog",
    "version": "1.0.0",
    "summary": "Operational catalog with idempotent sync",
    "author": "Manzano",
    "license": "LGPL-3",
    "depends": ["base", "mail"],
    "data": [
        "security/ir.model.access.csv",
        "data/catalog_seed.csv",
    ],
    "installable": True,
    "application": False,
}
