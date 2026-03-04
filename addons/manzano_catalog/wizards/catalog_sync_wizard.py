import csv
from io import StringIO

from odoo import models, fields


class ManzanoCatalogSyncWizard(models.TransientModel):
    _name = "manzano.catalog.sync.wizard"
    _description = "Manzano Catalog Sync Wizard"

    csv_content = fields.Text(required=True)
    source_name = fields.Char(default="manual_csv")
    result_summary = fields.Text(readonly=True)

    def action_sync(self):
        self.ensure_one()
        reader = csv.DictReader(StringIO(self.csv_content or ""))
        Item = self.env["manzano.catalog.item"]

        created = updated = skipped = errors = 0
        for row in reader:
            vals = {
                "external_ref": (row.get("external_ref") or "").strip(),
                "name": (row.get("name") or "").strip(),
                "category": (row.get("category") or "").strip(),
                "unit_type": (row.get("unit_type") or "service").strip(),
                "capacity_units": int(row.get("capacity_units") or 0),
                "price_base": float(row.get("price_base") or 0.0),
                "currency": (row.get("currency") or "CLP").strip(),
                "active": str(row.get("active") or "1").strip() in ("1", "true", "True", "yes"),
            }
            res = Item.upsert_from_dict(vals, source_name=self.source_name)
            st = res.get("status")
            if st == "created":
                created += 1
            elif st == "updated":
                updated += 1
            elif st == "skipped":
                skipped += 1
            else:
                errors += 1

        self.result_summary = f"created={created}, updated={updated}, skipped={skipped}, errors={errors}"
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }
