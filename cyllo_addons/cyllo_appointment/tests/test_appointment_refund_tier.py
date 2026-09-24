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

class TestAppointmentRefundTier(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.appointment_type = cls.env['appointment.type'].create({
            'name': 'Test Appointment Type',
            'duration': 1.0,
        })

    def test_check_percentage_valid(self):
        # Should not raise exception
        tier = self.env['appointment.refund.tier'].create({
            'appointment_type_id': self.appointment_type.id,
            'name': 'Full Refund',
            'hours_before': 48,
            'refund_percentage': 100.0,
        })
        self.assertEqual(tier.refund_percentage, 100.0)

    def test_check_percentage_invalid_low(self):
        with self.assertRaises(ValidationError):
            self.env['appointment.refund.tier'].create({
                'appointment_type_id': self.appointment_type.id,
                'name': 'Invalid Refund',
                'hours_before': 24,
                'refund_percentage': -10.0,
            })

    def test_check_percentage_invalid_high(self):
        with self.assertRaises(ValidationError):
            self.env['appointment.refund.tier'].create({
                'appointment_type_id': self.appointment_type.id,
                'name': 'Invalid Refund',
                'hours_before': 24,
                'refund_percentage': 110.0,
            })
