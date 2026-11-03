# -*- coding: utf-8 -*-
#############################################################################
#
#    Cyllo Pvt. Ltd.
#
#    Copyright (C) 2025-TODAY Cyllo(<https://www.cyllo.com>)
#    Author: Cyllo(<https://www.cyllo.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo import fields
from odoo.tests.common import TransactionCase
from datetime import timedelta

class TestSaleOrder(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({'name': 'Test Customer'})
        cls.product = cls.env['product.product'].create({
            'name': 'Appointment Service',
            'type': 'service',
            'list_price': 100.0,
        })
        cls.sale_order = cls.env['sale.order'].create({
            'partner_id': cls.partner.id,
            'order_line': [(0, 0, {
                'product_id': cls.product.id,
                'product_uom_qty': 1,
            })],
        })
        cls.appointment_type = cls.env['appointment.type'].create({
            'name': 'Paid Booking',
            'duration': 1.0,
            'require_staff': False,
        })

    def test_compute_appointment_count(self):
        self.env['appointment.appointment'].create({
            'name': 'Test Appt',
            'appointment_type_id': self.appointment_type.id,
            'sale_order_id': self.sale_order.id,
            'partner_id': self.partner.id,
        })
        self.sale_order._compute_appointment_count()
        self.assertEqual(self.sale_order.appointment_count, 1)

    def test_action_view_appointments(self):
        action = self.sale_order.action_view_appointments()
        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(action['res_model'], 'appointment.appointment')
        self.assertEqual(action['domain'], [('sale_order_id', '=', self.sale_order.id)])

    def test_action_confirm_auto_invoice(self):
        start = fields.Datetime.now() + timedelta(days=2)
        appt = self.env['appointment.appointment'].create({
            'name': 'Test Appt Pending',
            'appointment_type_id': self.appointment_type.id,
            'sale_order_id': self.sale_order.id,
            'state': 'pending_payment',
            'partner_id': self.partner.id,
            'start_datetime': start,
            'end_datetime': start + timedelta(hours=1),
        })
        self.sale_order.action_confirm()
        # Verify linked pending appointment is confirmed upon sale order confirmation
        self.assertEqual(appt.state, 'confirmed')
