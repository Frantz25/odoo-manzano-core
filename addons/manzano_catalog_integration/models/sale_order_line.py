from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    mz_catalog_item_id = fields.Many2one("manzano.catalog.item", string="Catalog Item")
    mz_catalog_external_ref = fields.Char(string="Catalog Ref", related="mz_catalog_item_id.external_ref", readonly=True)

    @api.onchange("mz_catalog_item_id")
    def _onchange_mz_catalog_item_id(self):
        for line in self:
            item = line.mz_catalog_item_id
            if not item:
                continue
            line.name = item.name
            line.price_unit = item.price_base
