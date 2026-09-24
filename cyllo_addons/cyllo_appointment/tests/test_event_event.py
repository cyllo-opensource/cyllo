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
from odoo.exceptions import UserError
from datetime import datetime, timedelta
import pytz

class TestEventEvent(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.employee = cls.env['hr.employee'].create({'name': 'Event Staff'})
        cls.appointment_type = cls.env['appointment.type'].create({
            'name': 'Event Booking',
            'scheduling_type': 'predefined',
            'duration': 1.0,
            'slot_interval': '60',
        })
        start_date = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(hours=4)
        cls.event = cls.env['event.event'].create({
            'name': 'Test Event',
            'date_begin': start_date,
            'date_end': end_date,
            'requires_appointment': True,
            'appointment_type_id': cls.appointment_type.id,
            'appointment_staff_ids': [(6, 0, [cls.employee.id])],
        })

    def test_action_generate_appointment_slots(self):
        # Should generate 4 slots (1 hour each over 4 hours)
        self.event.action_generate_appointment_slots()
        slots = self.env['appointment.slot'].search([('event_id', '=', self.event.id)])
        self.assertTrue(len(slots) > 0)

    def test_action_generate_appointment_slots_validation(self):
        self.event.requires_appointment = False
        with self.assertRaises(UserError):
            self.event.action_generate_appointment_slots()
        self.event.requires_appointment = True
        
        self.event.appointment_type_id = False
        with self.assertRaises(UserError):
            self.event.action_generate_appointment_slots()
        self.event.appointment_type_id = self.appointment_type.id

    def test_compute_appointment_count(self):
        self.event.action_generate_appointment_slots()
        slot = self.env['appointment.slot'].search([('event_id', '=', self.event.id)], limit=1)
        self.env['appointment.appointment'].create({
            'name': 'Event Appt',
            'appointment_type_id': self.appointment_type.id,
            'slot_id': slot.id,
            'state': 'confirmed',
        })
        self.event._compute_appointment_count()
        self.assertEqual(self.event.appointment_count, 1)

    def test_action_view_appointments(self):
        action = self.event.action_view_appointments()
        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(action['res_model'], 'appointment.appointment')
