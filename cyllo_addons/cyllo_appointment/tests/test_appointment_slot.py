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
import pytz


class TestAppointmentSlot(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.appointment_type = cls.env['appointment.type'].create({
            'name': 'Slot Test Type',
            'duration': 1.0,
            'slot_interval': '60',
            'scheduling_type': 'predefined',
            'require_staff': False,
            'require_resource': False,
        })
        # A slot in the near future with no staff/resource checks needed
        tomorrow_9am = datetime.now().replace(
            hour=9, minute=0, second=0, microsecond=0
        ) + timedelta(days=1)
        cls.slot = cls.env['appointment.slot'].create({
            'name': 'Test Slot',
            'appointment_type_id': cls.appointment_type.id,
            'start_datetime': tomorrow_9am,
            'end_datetime': tomorrow_9am + timedelta(hours=1),
        })

     
    # _compute_end_datetime
    def test_compute_end_datetime(self):
        """End datetime should be computed as start + duration."""
        new_start = datetime.now().replace(
            hour=10, minute=0, second=0, microsecond=0
        ) + timedelta(days=2)
        slot = self.env['appointment.slot'].create({
            'name': 'Auto End Slot',
            'appointment_type_id': self.appointment_type.id,
            'start_datetime': new_start,
            'end_datetime': new_start + timedelta(hours=1),
        })
        expected_end = new_start + timedelta(hours=self.appointment_type.duration)
        self.assertEqual(slot.end_datetime, expected_end)

     
    # _check_dates constraint
    def test_check_dates_valid(self):
        """Start before end → no error."""
        start = datetime.now() + timedelta(days=3, hours=9)
        slot = self.env['appointment.slot'].create({
            'name': 'Valid Dates',
            'appointment_type_id': self.appointment_type.id,
            'start_datetime': start,
            'end_datetime': start + timedelta(hours=1),
        })
        self.assertTrue(slot.id)

    def test_check_dates_invalid(self):
        """End before start → ValidationError."""
        start = datetime.now() + timedelta(days=3, hours=9)
        with self.assertRaises(ValidationError):
            self.env['appointment.slot'].create({
                'name': 'Invalid Dates',
                'appointment_type_id': self.appointment_type.id,
                'start_datetime': start,
                'end_datetime': start - timedelta(hours=1),
            })

     
    # _compute_booked_count / state
    def test_compute_booked_count_no_appointments(self):
        """A fresh slot should be available with 0 booked."""
        self.slot._compute_booked_count()
        self.assertEqual(self.slot.booked_count, 0)
        self.assertEqual(self.slot.state, 'available')
        self.assertTrue(self.slot.is_available)

    def test_compute_booked_count_with_appointment(self):
        """Booking an appointment changes the slot state accordingly."""
        partner = self.env['res.partner'].create({'name': 'Slot Customer'})
        appt = self.env['appointment.appointment'].create({
            'appointment_type_id': self.appointment_type.id,
            'slot_id': self.slot.id,
            'partner_id': partner.id,
            'start_datetime': self.slot.start_datetime,
            'end_datetime': self.slot.end_datetime,
            'state': 'confirmed',
            'attendee_count': 1,
        })
        self.slot._compute_booked_count()
        self.assertEqual(self.slot.booked_count, 1)

     
    # _compute_staff_resource_domain
    def test_compute_staff_resource_domain_no_staff(self):
        """Domain should be empty when no staff is on the appointment type."""
        self.slot._compute_staff_resource_domain()
        self.assertEqual(self.slot.staff_domain, '[]')
        self.assertEqual(self.slot.resource_domain, '[]')

    def test_compute_staff_resource_domain_with_staff(self):
        """Domain should include appointment type id when staff is linked."""
        employee = self.env['hr.employee'].create({'name': 'Domain Staff'})
        self.appointment_type.write({'staff_ids': [(4, employee.id)]})
        self.slot._compute_staff_resource_domain()
        self.assertIn(str(self.appointment_type.id), self.slot.staff_domain)

    # _check_required_assignments
    def test_check_required_staff_missing(self):
        """ValidationError when staff is required but not assigned."""
        appt_type = self.env['appointment.type'].create({
            'name': 'Staff Required Type',
            'duration': 1.0,
            'scheduling_type': 'predefined',
            'require_staff': True,
            'require_resource': False,
        })
        start = datetime.now() + timedelta(days=4, hours=9)
        with self.assertRaises(ValidationError):
            self.env['appointment.slot'].create({
                'name': 'No Staff Slot',
                'appointment_type_id': appt_type.id,
                'start_datetime': start,
                'end_datetime': start + timedelta(hours=1),
            })
