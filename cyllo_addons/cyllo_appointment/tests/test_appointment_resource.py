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

class TestAppointmentResource(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.resource = cls.env['appointment.resource'].create({
            'name': 'Test Room',
            'resource_type': 'room',
            'capacity': 5,
        })
        cls.appointment_type = cls.env['appointment.type'].create({
            'name': 'Room Booking',
            'duration': 1.0,
        })

    def test_compute_appointment_count(self):
        # Create an appointment linked to the resource
        self.env['appointment.appointment'].create({
            'name': 'Test Appointment',
            'appointment_type_id': self.appointment_type.id,
            'resource_id': self.resource.id,
        })
        self.resource._compute_appointment_count()
        self.assertEqual(self.resource.appointment_count, 1)

    def test_action_view_appointments(self):
        action = self.resource.action_view_appointments()
        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(action['res_model'], 'appointment.appointment')
        self.assertEqual(action['domain'], [('resource_id', '=', self.resource.id)])
        self.assertEqual(action['context']['default_resource_id'], self.resource.id)
