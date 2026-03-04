from datetime import timedelta
import secrets

from odoo import api, fields, models, _


class ManzanoBooking(models.Model):
    _name = "manzano.booking"
    _description = "Manzano Booking"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    sale_order_id = fields.Many2one("sale.order", required=True, ondelete="cascade", index=True)
    partner_id = fields.Many2one(related="sale_order_id.partner_id", store=True, readonly=True)

    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("reserved", "Reserved"),
            ("confirmed", "Confirmed"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
        required=True,
        tracking=True,
    )

    hold_expires_at = fields.Datetime(string="Hold Expires At", tracking=True)
    qr_token = fields.Char(string="QR Token", copy=False, index=True)

    @api.model
    def _mz_default_hold_hours(self):
        val = self.env["ir.config_parameter"].sudo().get_param("manzano_booking.soft_hold_hours", "24")
        try:
            return max(int(val), 1)
        except Exception:
            return 24

    @api.model
    def cron_expire_soft_holds(self):
        now = fields.Datetime.now()
        expired = self.search([
            ("state", "=", "reserved"),
            ("hold_expires_at", "!=", False),
            ("hold_expires_at", "<", now),
        ])
        for booking in expired:
            booking.write({"state": "cancelled"})
            if booking.sale_order_id:
                booking.sale_order_id.message_post(
                    body=_("Soft-hold expirado automáticamente. Reserva tentativa cancelada.")
                )
        return True

    def set_soft_hold(self):
        for booking in self:
            hours = booking._mz_default_hold_hours()
            booking.write({
                "state": "reserved",
                "hold_expires_at": fields.Datetime.now() + timedelta(hours=hours),
                "qr_token": booking.qr_token or secrets.token_urlsafe(12),
            })

    def set_confirmed(self):
        for booking in self:
            booking.write({
                "state": "confirmed",
                "hold_expires_at": False,
                "qr_token": booking.qr_token or secrets.token_urlsafe(12),
            })
