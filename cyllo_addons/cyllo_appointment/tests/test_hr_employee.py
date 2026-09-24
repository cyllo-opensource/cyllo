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
from datetime import timedelta
from odoo import fields

class TestHrEmployee(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Test Employee',
        })
        cls.appointment_type = cls.env['appointment.type'].create({
            'name': 'Staff Booking',
            'duration': 1.0,
        })

    def test_compute_appointment_count(self):
        now = fields.Datetime.now()
        # Past appointment
        self.env['appointment.appointment'].create({
            'name': 'Past Appt',
            'appointment_type_id': self.appointment_type.id,
            'staff_id': self.employee.id,
            'start_datetime': now - timedelta(days=1),
            'state': 'done',
        })
        # Upcoming appointment
        self.env['appointment.appointment'].create({
            'name': 'Upcoming Appt',
            'appointment_type_id': self.appointment_type.id,
            'staff_id': self.employee.id,
            'start_datetime': now + timedelta(days=1),
            'state': 'confirmed',
        })
        
        self.employee._compute_appointment_count()
        self.assertEqual(self.employee.appointment_count, 2)
        self.assertEqual(self.employee.upcoming_appointment_count, 1)

    def test_action_view_appointments(self):
        action = self.employee.action_view_appointments()
        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(action['res_model'], 'appointment.appointment')
        self.assertEqual(action['domain'], [('staff_id', '=', self.employee.id)])
        self.assertEqual(action['context']['default_staff_id'], self.employee.id)
