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
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
from odoo import fields


class TestAppointmentType(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.appt_type = cls.env['appointment.type'].create({
            'name': 'Test Type',
            'duration': 1.0,
            'slot_interval': '60',
            'min_booking_notice': 1.0,
            'refund_policy': 'none',
            'is_paid': False,
            'require_staff': False,
        })

    def test_compute_website_url(self):
        self.appt_type._compute_website_url()
        self.assertEqual(self.appt_type.website_url, '/appointment/%s' % self.appt_type.id)

    def test_compute_appointment_count_empty(self):
        self.appt_type._compute_appointment_count()
        self.assertEqual(self.appt_type.appointment_count, 0)

    def test_compute_appointment_count_with_future_appointment(self):
        partner = self.env['res.partner'].create({'name': 'Type Count Customer'})
        future_start = fields.Datetime.now() + timedelta(days=2)
        self.env['appointment.appointment'].create({
            'appointment_type_id': self.appt_type.id,
            'partner_id': partner.id,
            'start_datetime': future_start,
            'end_datetime': future_start + timedelta(hours=1),
            'state': 'confirmed',
        })
        self.appt_type._compute_appointment_count()
        self.assertGreaterEqual(self.appt_type.appointment_count, 1)
        self.assertGreaterEqual(self.appt_type.upcoming_appointment_count, 1)

    def test_check_duration_valid(self):
        appt = self.env['appointment.type'].create({'name': 'Pos Duration', 'duration': 2.0, 'require_staff': False})
        self.assertEqual(appt.duration, 2.0)

    def test_check_duration_zero_invalid(self):
        with self.assertRaises(ValidationError):
            self.env['appointment.type'].create({'name': 'Zero Duration', 'duration': 0.0, 'require_staff': False})

    def test_check_duration_negative_invalid(self):
        with self.assertRaises(ValidationError):
            self.env['appointment.type'].create({'name': 'Neg Duration', 'duration': -1.0, 'require_staff': False})

    def test_check_min_booking_notice_zero_valid(self):
        appt = self.env['appointment.type'].create({'name': 'Zero Notice', 'duration': 1.0, 'min_booking_notice': 0.0, 'require_staff': False})
        self.assertEqual(appt.min_booking_notice, 0.0)

    def test_check_min_booking_notice_negative_invalid(self):
        with self.assertRaises(ValidationError):
            self.env['appointment.type'].create({'name': 'Neg Notice', 'duration': 1.0, 'min_booking_notice': -5.0, 'require_staff': False})

    def test_check_reminder_hours_valid(self):
        appt = self.env['appointment.type'].create({'name': 'Reminder Valid', 'duration': 1.0, 'reminder_hours_before': '24,2', 'require_staff': False})
        self.assertEqual(appt.reminder_hours_before, '24,2')

    def test_check_reminder_hours_invalid(self):
        with self.assertRaises(ValidationError):
            self.env['appointment.type'].create({'name': 'Bad Reminder', 'duration': 1.0, 'reminder_hours_before': 'abc', 'require_staff': False})

    def test_check_refund_policy_free_appointment_no_refund_ok(self):
        # None policy on unpaid → OK
        appt = self.env['appointment.type'].create({'name': 'Free None', 'duration': 1.0, 'is_paid': False, 'refund_policy': 'none', 'require_staff': False})
        self.assertEqual(appt.refund_policy, 'none')

    def test_check_refund_policy_not_paid_raises(self):
        with self.assertRaises(ValidationError):
            self.env['appointment.type'].create({'name': 'Free Full', 'duration': 1.0, 'is_paid': False, 'refund_policy': 'full', 'require_staff': False})

    def test_check_refund_policy_partial_out_of_range(self):
        with self.assertRaises(ValidationError):
            self.env['appointment.type'].create({'name': 'Bad Partial', 'duration': 1.0, 'is_paid': True, 'refund_policy': 'partial', 'refund_percentage': 150.0, 'require_staff': False})

    def test_get_refund_percentage_none_policy(self):
        pct = self.appt_type.get_refund_percentage(datetime.now(), datetime.now() + timedelta(hours=2))
        self.assertEqual(pct, 0.0)

    def test_get_refund_percentage_full_policy(self):
        appt = self.env['appointment.type'].create({'name': 'Full', 'duration': 1.0, 'is_paid': True, 'refund_policy': 'full', 'require_staff': False})
        self.assertEqual(appt.get_refund_percentage(datetime.now(), datetime.now() + timedelta(hours=2)), 100.0)

    def test_get_refund_percentage_credit_policy(self):
        appt = self.env['appointment.type'].create({'name': 'Credit', 'duration': 1.0, 'is_paid': True, 'refund_policy': 'credit', 'require_staff': False})
        self.assertEqual(appt.get_refund_percentage(datetime.now(), datetime.now() + timedelta(hours=2)), 100.0)

    def test_get_refund_percentage_partial_flat(self):
        appt = self.env['appointment.type'].create({'name': 'Partial Flat', 'duration': 1.0, 'is_paid': True, 'refund_policy': 'partial', 'refund_percentage': 75.0, 'require_staff': False})
        self.assertEqual(appt.get_refund_percentage(datetime.now(), datetime.now() + timedelta(hours=2)), 75.0)

    def test_get_refund_percentage_tiered(self):
        appt = self.env['appointment.type'].create({
            'name': 'Tiered',
            'duration': 1.0,
            'is_paid': True,
            'refund_policy': 'partial',
            'refund_percentage': 0.0,
            'require_staff': False,
            'refund_tier_ids': [
                (0, 0, {'name': 'Full Tier', 'hours_before': 48, 'refund_percentage': 100.0}),
                (0, 0, {'name': 'Half Tier', 'hours_before': 24, 'refund_percentage': 50.0}),
            ],
        })
        # 72h before → 100%
        self.assertEqual(appt.get_refund_percentage(datetime.now(), datetime.now() + timedelta(hours=72)), 100.0)
        # 30h before → 50%
        self.assertEqual(appt.get_refund_percentage(datetime.now(), datetime.now() + timedelta(hours=30)), 50.0)
        # 10h before → 0%
        self.assertEqual(appt.get_refund_percentage(datetime.now(), datetime.now() + timedelta(hours=10)), 0.0)

    def test_action_view_appointments(self):
        action = self.appt_type.action_view_appointments()
        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(action['res_model'], 'appointment.appointment')
        self.assertIn(('appointment_type_id', '=', self.appt_type.id), action['domain'])
