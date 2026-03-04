from datetime import timedelta

from odoo import fields
from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import UserError


@tagged('post_install', '-at_install')
class TestManzanoBookingFlow(TransactionCase):

    def setUp(self):
        super().setUp()
        self.partner = self.env['res.partner'].create({'name': 'Cliente QA'})
        self.product = self.env['product.product'].create({
            'name': 'Servicio QA',
            'type': 'service',
            'list_price': 100.0,
        })

    def _new_booking_order(self, policy=True):
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'mz_is_booking': True,
            'mz_policy_accepted': policy,
            'order_line': [(0, 0, {
                'name': 'Línea QA',
                'product_id': self.product.id,
                'product_uom_qty': 1,
                'price_unit': 100.0,
            })],
        })
        return order

    def test_happy_path_confirm_sets_booking_confirmed_and_qr_definitive(self):
        order = self._new_booking_order(policy=True)
        order.action_mz_create_soft_hold()
        self.assertEqual(order.mz_booking_state, 'reserved')
        self.assertEqual(order.mz_qr_state, 'provisional')

        order.action_confirm()
        self.assertEqual(order.state, 'sale')
        self.assertEqual(order.mz_booking_state, 'confirmed')
        self.assertEqual(order.mz_qr_state, 'definitive')

    def test_block_when_policy_not_accepted(self):
        order = self._new_booking_order(policy=False)
        order.action_mz_create_soft_hold()
        with self.assertRaises(UserError):
            order.action_confirm()
        self.assertNotEqual(order.state, 'sale')
        self.assertIn(order.mz_booking_state, ('draft', 'reserved'))

    def test_expired_soft_hold_is_cancelled_and_qr_invalid(self):
        order = self._new_booking_order(policy=True)
        order.action_mz_create_soft_hold()
        booking = order.mz_booking_id
        self.assertEqual(booking.state, 'reserved')

        booking.write({'hold_expires_at': fields.Datetime.now() - timedelta(minutes=5)})
        self.env['manzano.booking'].cron_expire_soft_holds()

        self.assertEqual(booking.state, 'cancelled')
        self.assertEqual(booking.qr_state, 'invalid')
