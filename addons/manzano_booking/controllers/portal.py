from odoo import http
from odoo.http import request


class ManzanoBookingPortal(http.Controller):

    def _get_booking(self, token):
        if not token:
            return False
        return request.env["manzano.booking"].sudo().search([("portal_token", "=", token)], limit=1)

    @http.route("/manzano/booking/<string:token>", type="http", auth="public", website=True)
    def booking_portal_view(self, token, **kwargs):
        booking = self._get_booking(token)
        if not booking:
            return request.not_found()

        return request.render("manzano_booking.portal_booking_page", {
            "booking": booking,
            "order": booking.sale_order_id,
        })

    @http.route("/manzano/booking/<string:token>/accept_policy", type="http", auth="public", methods=["POST"], website=True, csrf=True)
    def booking_portal_accept_policy(self, token, **kwargs):
        booking = self._get_booking(token)
        if not booking:
            return request.not_found()

        order = booking.sale_order_id
        order.sudo().write({"mz_policy_accepted": True})
        order.message_post(body="Policy accepted from client portal.")

        return request.redirect(f"/manzano/booking/{token}")
