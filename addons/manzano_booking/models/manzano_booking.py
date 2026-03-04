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
    portal_token = fields.Char(string="Portal Token", copy=False, index=True)
    qr_state = fields.Selection(
        [
            ("none", "No QR"),
            ("provisional", "Provisional"),
            ("definitive", "Definitive"),
            ("invalid", "Invalid"),
        ],
        string="QR State",
        default="none",
        tracking=True,
    )
    qr_url = fields.Char(string="QR URL", compute="_compute_qr_url", store=False)
    portal_url = fields.Char(string="Portal URL", compute="_compute_portal_url", store=False)

    @api.depends("qr_token", "qr_state")
    def _compute_qr_url(self):
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url") or ""
        for rec in self:
            if not (rec.qr_token and rec.qr_state in ("provisional", "definitive") and base_url):
                rec.qr_url = False
                continue
            rec.qr_url = f"{base_url}/manzano/checkin/{rec.qr_token}?mode={rec.qr_state}"

    @api.depends("portal_token")
    def _compute_portal_url(self):
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url") or ""
        for rec in self:
            rec.portal_url = f"{base_url}/manzano/booking/{rec.portal_token}" if (base_url and rec.portal_token) else False

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
            booking.write({"state": "cancelled", "qr_state": "invalid"})
            if booking.sale_order_id:
                booking.sale_order_id.message_post(
                    body=_("Soft-hold expirado automáticamente. Reserva tentativa cancelada y QR invalidado.")
                )
        return True

    def set_soft_hold(self):
        for booking in self:
            hours = booking._mz_default_hold_hours()
            booking.write({
                "state": "reserved",
                "hold_expires_at": fields.Datetime.now() + timedelta(hours=hours),
                "qr_token": booking.qr_token or secrets.token_urlsafe(12),
                "portal_token": booking.portal_token or secrets.token_urlsafe(24),
                "qr_state": "provisional",
            })

    def set_confirmed(self):
        for booking in self:
            booking.write({
                "state": "confirmed",
                "hold_expires_at": False,
                "qr_token": booking.qr_token or secrets.token_urlsafe(12),
                "portal_token": booking.portal_token or secrets.token_urlsafe(24),
                "qr_state": "definitive",
            })

    def set_cancelled(self):
        for booking in self:
            booking.write({
                "state": "cancelled",
                "qr_state": "invalid",
            })
