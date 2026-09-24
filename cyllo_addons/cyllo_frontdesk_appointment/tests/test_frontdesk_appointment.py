# -*- coding: utf-8 -*-
#############################################################################
#
#    Cyllo Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cyllo(<https://www.cyllo.com>)
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

class TestFrontdeskAppointment(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(TestFrontdeskAppointment, cls).setUpClass()
        cls.partner = cls.env['res.partner'].create({
            'name': 'Test Partner',
            'email': 'test@example.com',
            'phone': '1234567890'
        })
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Test Employee',
            'work_email': 'test@example.com',
        })
        cls.station = cls.env['frontdesk.frontdesk'].create({
            'name': 'Test Station',
            'is_host': True,
            'is_drink': True,
        })
        cls.app_type = cls.env['appointment.type'].create({
            'name': 'Test App Type',
            'station_id': cls.station.id,
            'duration': 1.0,
        })

    def test_01_appointment_creates_visitor(self):
        """Test that confirming an appointment creates a visitor at the linked station."""
        appointment = self.env['appointment.appointment'].create({
            'partner_id': self.partner.id,
            'appointment_type_id': self.app_type.id,
            'start_datetime': '2026-07-01 10:00:00',
            'end_datetime': '2026-07-01 11:00:00',
            'staff_id' : self.employee.id
        })
        appointment.write({'state': 'confirmed'})
        visitor = self.env['frontdesk.visitor'].search([('appointment_id', '=', appointment.id)])
        self.assertTrue(visitor, "A visitor should have been created for the confirmed appointment.")
        self.assertEqual(visitor.station_id, self.station, "Visitor should be assigned to the appointment's station.")
        self.assertEqual(visitor.state, 'draft', "Visitor should be in 'draft' state.")

    def test_02_visitor_checkin_starts_appointment(self):
        """Test that checking in a visitor moves the appointment to 'in_progress'."""
        appointment = self.env['appointment.appointment'].create({
            'partner_id': self.partner.id,
            'appointment_type_id': self.app_type.id,
            'start_datetime': '2026-07-01 10:00:00',
            'end_datetime': '2026-07-01 11:00:00',
            'staff_id': self.employee.id,
        })
        appointment.write({'state': 'confirmed'})
        visitor = self.env['frontdesk.visitor'].search([('appointment_id', '=', appointment.id)])
        self.assertTrue(visitor, "Visitor should be created on confirmed state.")
        visitor.write({'state': 'planned'})
        visitor.action_check_in()
        self.assertEqual(visitor.state, 'checked_in')
        self.assertEqual(appointment.state, 'in_progress', "Appointment state should be 'in_progress' after visitor check-in.")

    def test_03_visitor_checkout_completes_appointment(self):
        """Test that checking out a visitor moves the appointment to 'done'."""
        appointment = self.env['appointment.appointment'].create({
            'partner_id': self.partner.id,
            'appointment_type_id': self.app_type.id,
            'start_datetime': '2026-07-01 10:00:00',
            'end_datetime': '2026-07-01 11:00:00',
            'staff_id': self.employee.id,
            'state': 'confirmed'
        })
        
        visitor = self.env['frontdesk.visitor'].search([('appointment_id', '=', appointment.id)])
        visitor.write({'state': 'planned'})
        visitor.action_check_in()
        visitor.action_check_out()
        self.assertEqual(visitor.state, 'checked_out')
        self.assertEqual(appointment.state, 'done', "Appointment state should be 'done' after visitor check-out.")

    def test_04_visitor_cancel_cancels_appointment(self):
        """Test that canceling a visitor cancels the linked appointment."""
        appointment = self.env['appointment.appointment'].create({
            'partner_id': self.partner.id,
            'appointment_type_id': self.app_type.id,
            'start_datetime': '2026-07-01 10:00:00',
            'end_datetime': '2026-07-01 11:00:00',
            'staff_id': self.employee.id,
            'state': 'confirmed'
        })
        visitor = self.env['frontdesk.visitor'].search([('appointment_id', '=', appointment.id)])
        visitor.action_cancel()
        self.assertEqual(visitor.state, 'cancelled')
        self.assertEqual(appointment.state, 'cancelled', "Appointment state should be 'cancelled' after visitor cancellation.")

    def test_05_book_now_action(self):
        """Test that action_book_now opens the wizard correctly with pre-filled context."""
        visitor = self.env['frontdesk.visitor'].create({
            'name': 'Walk-in Visitor',
            'station_id': self.station.id,
            'visitor_name': 'Walk-in Visitor',
            'email': 'walkin@example.com',
            'phone': '9876543210',
            'state': 'planned'
        })
        action = visitor.action_book_now()
        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(action['res_model'], 'appointment.appointment')
        context = action.get('context', {})
        self.assertEqual(context.get('default_visitor_id'), visitor.id)
        self.assertEqual(context.get('default_station_id'), self.station.id)
        # Verify partner was created and linked
        self.assertTrue(visitor.partner_id, "Partner should have been created or linked during action_book_now.")
        self.assertEqual(visitor.partner_id.email, 'walkin@example.com')

    def test_06_appointment_state_changes_visitor(self):
        """Test that appointment state changes affect the visitor."""
        appointment = self.env['appointment.appointment'].create({
            'partner_id': self.partner.id,
            'appointment_type_id': self.app_type.id,
            'start_datetime': '2026-07-01 10:00:00',
            'end_datetime': '2026-07-01 11:00:00',
            'staff_id': self.employee.id
        })
        appointment.write({'state': 'confirmed'})
        visitor = self.env['frontdesk.visitor'].search([('appointment_id', '=', appointment.id)])
        visitor.write({'state': 'planned'})
        # Appointment starts, visitor checks in
        appointment.write({'state': 'in_progress'})
        self.assertEqual(visitor.state, 'checked_in')
        # Appointment completes, visitor checks out
        appointment.write({'state': 'done'})
        self.assertEqual(visitor.state, 'checked_out')
