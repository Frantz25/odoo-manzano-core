from odoo import fields, models, _
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    mz_is_booking = fields.Boolean(string="Is Manzano Booking", default=False, index=True)
    mz_policy_accepted = fields.Boolean(string="Policy Accepted", default=False, copy=False)
    mz_booking_id = fields.Many2one("manzano.booking", string="Booking", copy=False, readonly=True)
    mz_booking_state = fields.Selection(related="mz_booking_id.state", string="Booking State", readonly=True)
    mz_hold_expires_at = fields.Datetime(related="mz_booking_id.hold_expires_at", string="Hold Expires", readonly=True)
    mz_qr_state = fields.Selection(related="mz_booking_id.qr_state", string="QR State", readonly=True)
    mz_qr_url = fields.Char(related="mz_booking_id.qr_url", string="QR URL", readonly=True)

    def _mz_validate_for_final_confirmation(self):
        for order in self.filtered("mz_is_booking"):
            if not order.partner_id:
                raise UserError(_("Booking requires a customer before confirmation."))
            if not order.mz_policy_accepted:
                raise UserError(_("Policy acceptance is required before final confirmation."))
            if not order.mz_booking_id:
                raise UserError(_("Booking record is required before final confirmation."))
            if order.mz_booking_id.state not in ("reserved", "draft"):
                raise UserError(_("Booking must be in draft/reserved before final confirmation."))
            # NOTE (E2.2): availability and deposit validators are added in next commits.

    def _mz_get_or_create_booking(self):
        self.ensure_one()
        if self.mz_booking_id:
            return self.mz_booking_id
        booking = self.env["manzano.booking"].create({
            "sale_order_id": self.id,
            "state": "draft",
            "qr_state": "none",
        })
        self.mz_booking_id = booking.id
        return booking

    def _mz_confirm_booking_atomic(self):
        booking_orders = self.filtered("mz_is_booking")

        # 1) pre-validations (fail-fast)
        booking_orders._mz_validate_for_final_confirmation()

        # 2) commercial confirmation (if this fails, Odoo transaction rolls back)
        res = super(SaleOrder, self).action_confirm()

        # 3) operational confirmation must be consistent with sale state
        for order in booking_orders:
            booking = order._mz_get_or_create_booking()
            booking.set_confirmed()

        return res

    def action_confirm(self):
        return self._mz_confirm_booking_atomic()

    def action_cancel(self):
        res = super().action_cancel()
        for order in self.filtered("mz_is_booking"):
            if order.mz_booking_id:
                order.mz_booking_id.set_cancelled()
        return res

    def action_mz_create_soft_hold(self):
        for order in self:
            if not order.mz_is_booking:
                raise UserError(_("Order is not marked as Manzano booking."))
            if not order.partner_id:
                raise UserError(_("Customer is required before creating soft-hold."))
            booking = order._mz_get_or_create_booking()
            booking.set_soft_hold()
            order.message_post(body=_("Soft-hold creado con expiración en %s") % (booking.hold_expires_at or "-"))
        return True
