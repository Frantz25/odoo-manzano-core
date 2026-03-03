from odoo import fields, models


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
