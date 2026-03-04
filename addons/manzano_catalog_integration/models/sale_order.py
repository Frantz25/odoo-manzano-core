from odoo import models, _
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _mz_validate_catalog_items_before_confirm(self):
        for order in self:
            invalid = order.order_line.filtered(lambda l: l.mz_catalog_item_id and not l.mz_catalog_item_id.active)
            if invalid:
                refs = ", ".join(i.mz_catalog_item_id.external_ref for i in invalid if i.mz_catalog_item_id)
                raise UserError(_("No se puede confirmar: hay ítems de catálogo inactivos: %s") % refs)

    def action_confirm(self):
        self._mz_validate_catalog_items_before_confirm()
        return super().action_confirm()
