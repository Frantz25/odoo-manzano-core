import hashlib
import json

from odoo import fields, models, api


class ManzanoCatalogItem(models.Model):
    _name = "manzano.catalog.item"
    _description = "Manzano Catalog Item"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "name"

    external_ref = fields.Char(required=True, index=True, tracking=True)
    name = fields.Char(required=True, tracking=True)
    category = fields.Char(index=True)
    unit_type = fields.Selection(
        [("room", "Room"), ("space", "Space"), ("pool", "Pool"), ("service", "Service")],
        default="service",
        required=True,
    )
    capacity_units = fields.Integer(default=0)
    price_base = fields.Float(default=0.0)
    currency = fields.Char(default="CLP")
    active = fields.Boolean(default=True)

    # Campos adicionales útiles para catálogo real
    source_default_code = fields.Char(index=True)
    source_type = fields.Char()
    source_tax = fields.Char()
    source_uom = fields.Char()
    source_charge_mode = fields.Char(index=True)
    source_min_people = fields.Integer(default=0)

    source_hash = fields.Char(index=True)
    source_name = fields.Char(default="csv")
    last_sync_at = fields.Datetime()

    _sql_constraints = [
        ("manzano_catalog_external_ref_uniq", "unique(external_ref)", "external_ref must be unique."),
    ]

    @api.model
    def _compute_row_hash(self, vals):
        payload = {
            "external_ref": vals.get("external_ref"),
            "name": vals.get("name"),
            "category": vals.get("category"),
            "unit_type": vals.get("unit_type"),
            "capacity_units": vals.get("capacity_units"),
            "price_base": vals.get("price_base"),
            "currency": vals.get("currency"),
            "active": vals.get("active", True),
            "source_type": vals.get("source_type"),
            "source_tax": vals.get("source_tax"),
            "source_uom": vals.get("source_uom"),
            "source_charge_mode": vals.get("source_charge_mode"),
            "source_min_people": vals.get("source_min_people"),
        }
        raw = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @api.model
    def upsert_from_dict(self, vals, source_name="csv"):
        ext = vals.get("external_ref")
        if not ext:
            return {"status": "error", "reason": "missing_external_ref"}

        row_hash = self._compute_row_hash(vals)
        rec = self.search([("external_ref", "=", ext)], limit=1)

        data = dict(vals)
        data["source_hash"] = row_hash
        data["source_name"] = source_name
        data["last_sync_at"] = fields.Datetime.now()

        if not rec:
            self.create(data)
            return {"status": "created", "external_ref": ext}

        if rec.source_hash == row_hash:
            return {"status": "skipped", "external_ref": ext}

        rec.write(data)
        return {"status": "updated", "external_ref": ext}
