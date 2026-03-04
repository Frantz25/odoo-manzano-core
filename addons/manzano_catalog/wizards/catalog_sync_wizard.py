import csv
from io import StringIO

from odoo import fields, models


class ManzanoCatalogSyncWizard(models.TransientModel):
    _name = "manzano.catalog.sync.wizard"
    _description = "Manzano Catalog Sync Wizard"

    csv_content = fields.Text(required=True)
    source_name = fields.Char(default="manual_csv")
    result_summary = fields.Text(readonly=True)

    def _map_charge_mode_to_unit_type(self, charge_mode):
        cm = (charge_mode or "").strip().lower()
        if cm == "room_person_night":
            return "room"
        if cm == "day":
            return "space"
        if cm == "pool":
            return "pool"
        return "service"

    def _to_bool(self, value):
        return str(value or "").strip().lower() in ("1", "true", "yes", "y", "si", "sí")

    def _to_int(self, value, default=0):
        try:
            return int(float(str(value or default).strip()))
        except Exception:
            return default

    def _to_float(self, value, default=0.0):
        try:
            return float(str(value or default).strip().replace(",", "."))
        except Exception:
            return default

    def _row_to_catalog_vals(self, row):
        # Formato nuevo (normalizado)
        if row.get("external_ref"):
            return {
                "external_ref": (row.get("external_ref") or "").strip(),
                "source_default_code": (row.get("external_ref") or "").strip(),
                "name": (row.get("name") or "").strip(),
                "category": (row.get("category") or "").strip(),
                "unit_type": (row.get("unit_type") or "service").strip(),
                "capacity_units": self._to_int(row.get("capacity_units"), 0),
                "price_base": self._to_float(row.get("price_base"), 0.0),
                "currency": (row.get("currency") or "CLP").strip(),
                "active": self._to_bool(row.get("active") if row.get("active") is not None else "1"),
            }

        # Formato real legado (default_code,name,type,list_price,tax,categ,uom,active,charge_mode,min_people)
        default_code = (row.get("default_code") or "").strip()
        charge_mode = (row.get("charge_mode") or "").strip()
        return {
            "external_ref": default_code,
            "source_default_code": default_code,
            "name": (row.get("name") or "").strip(),
            "category": (row.get("categ") or "").strip(),
            "unit_type": self._map_charge_mode_to_unit_type(charge_mode),
            "capacity_units": self._to_int(row.get("min_people"), 0),
            "price_base": self._to_float(row.get("list_price"), 0.0),
            "currency": "CLP",
            "active": self._to_bool(row.get("active") if row.get("active") is not None else "1"),
            "source_type": (row.get("type") or "").strip(),
            "source_tax": (row.get("tax") or "").strip(),
            "source_uom": (row.get("uom") or "").strip(),
            "source_charge_mode": charge_mode,
            "source_min_people": self._to_int(row.get("min_people"), 0),
        }

    def action_sync(self):
        self.ensure_one()
        reader = csv.DictReader(StringIO(self.csv_content or ""))
        Item = self.env["manzano.catalog.item"]

        created = updated = skipped = errors = 0
        for row in reader:
            vals = self._row_to_catalog_vals(row)
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
