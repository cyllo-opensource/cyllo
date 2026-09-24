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
from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.fields import Datetime
from datetime import timedelta

@tagged('post_install', '-at_install')
class TestAppointmentCrm(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.staff_user = cls.env['res.users'].create({
            'name': 'Test Staff',
            'login': 'test_staff',
            'email': 'staff@example.com',
            'groups_id': [(6, 0, [cls.env.ref('base.group_user').id, cls.env.ref('sales_team.group_sale_salesman').id])]
        })
        # Staff employee
        cls.staff_employee = cls.env['hr.employee'].create({
            'name': 'Test Staff Employee',
            'user_id': cls.staff_user.id,
        })
        cls.customer = cls.env['res.partner'].create({
            'name': 'Test Customer',
            'email': 'customer@example.com',
        })
        cls.appt_type_no_lead = cls.env['appointment.type'].create({
            'name': 'No Lead Type',
            'lead_create': False,
        })
        cls.appt_type_lead = cls.env['appointment.type'].create({
            'name': 'Lead Creation Type',
            'lead_create': True,
        })

    def test_01_no_lead_created_when_lead_create_false(self):
        appointment = self.env['appointment.appointment'].create({
            'appointment_type_id': self.appt_type_no_lead.id,
            'partner_id': self.customer.id,
            'staff_id': self.staff_employee.id,
            'start_datetime': Datetime.now() + timedelta(days=1),
            'end_datetime': Datetime.now() + timedelta(days=1, hours=1),
            'state': 'draft',
        })
        appointment.action_confirm()
        # Verify no opportunity was linked or created
        self.assertFalse(appointment.opportunity_id)
        
    def test_02_lead_created_when_lead_create_true(self):
        appointment = self.env['appointment.appointment'].create({
            'appointment_type_id': self.appt_type_lead.id,
            'partner_id': self.customer.id,
            'staff_id': self.staff_employee.id,
            'start_datetime': Datetime.now() + timedelta(days=1),
            'end_datetime': Datetime.now() + timedelta(days=1, hours=1),
            'state': 'draft',
        })
        appointment.action_confirm()
        self.assertTrue(appointment.opportunity_id)
        opp = appointment.opportunity_id
        self.assertEqual(opp.partner_id.id, self.customer.id)
        self.assertEqual(opp.user_id.id, self.staff_user.id)
        activity = self.env['mail.activity'].search([
            ('res_model', '=', 'crm.lead'),
            ('res_id', '=', opp.id),
            ('activity_type_id', '=', self.env.ref('mail.mail_activity_data_meeting').id)
        ])
        self.assertTrue(activity)
        
        # Verify appointment type lead_ids and count
        self.appt_type_lead.invalidate_recordset(['lead_ids', 'lead_count'])
        appt_type = self.appt_type_lead.with_context(allowed_company_ids=[self.env.company.id])
        self.assertIn(opp.id, appt_type.lead_ids.ids)
        self.assertEqual(appt_type.lead_count, len(appt_type.lead_ids))
        
    def test_03_existing_lead_linked(self):
        """Create an existing open lead for the same customer and staff"""
        existing_lead = self.env['crm.lead'].create({
            'name': 'Existing Lead',
            'partner_id': self.customer.id,
            'user_id': self.staff_user.id,
            'type': 'opportunity',
        })
        
        appointment = self.env['appointment.appointment'].create({
            'appointment_type_id': self.appt_type_lead.id,
            'partner_id': self.customer.id,
            'staff_id': self.staff_employee.id,
            'start_datetime': Datetime.now() + timedelta(days=2),
            'end_datetime': Datetime.now() + timedelta(days=2, hours=1),
            'state': 'draft',
        })
        appointment.action_confirm()
        self.assertEqual(appointment.opportunity_id.id, existing_lead.id)
        
    def test_04_action_methods(self):
        appointment = self.env['appointment.appointment'].create({
            'appointment_type_id': self.appt_type_lead.id,
            'partner_id': self.customer.id,
            'staff_id': self.staff_employee.id,
            'start_datetime': Datetime.now() + timedelta(days=3),
            'end_datetime': Datetime.now() + timedelta(days=3, hours=1),
            'state': 'draft',
        })
        appointment.action_confirm()
        # Test action_view_opportunity
        action_opp = appointment.action_view_opportunity()
        self.assertEqual(action_opp['res_id'], appointment.opportunity_id.id)
        self.assertEqual(action_opp['res_model'], 'crm.lead')
        # Test action_appointment_leads
        action_leads = self.appt_type_lead.action_appointment_leads()
        self.assertEqual(action_leads['domain'][0][1], 'in')
        self.assertEqual(action_leads['res_model'], 'crm.lead')

    def test_05_create_confirmed_appointment(self):
        appointment = self.env['appointment.appointment'].create({
            'appointment_type_id': self.appt_type_lead.id,
            'partner_id': self.customer.id,
            'staff_id': self.staff_employee.id,
            'start_datetime': Datetime.now() + timedelta(days=4),
            'end_datetime': Datetime.now() + timedelta(days=4, hours=1),
            'state': 'confirmed',
        })
        # Verify opportunity was linked and created during create() method
        self.assertTrue(appointment.opportunity_id)

    def test_06_write_confirmed_appointment(self):
        appointment = self.env['appointment.appointment'].create({
            'appointment_type_id': self.appt_type_lead.id,
            'partner_id': self.customer.id,
            'staff_id': self.staff_employee.id,
            'start_datetime': Datetime.now() + timedelta(days=5),
            'end_datetime': Datetime.now() + timedelta(days=5, hours=1),
            'state': 'draft',
        })
        # Verify no opportunity initially
        self.assertFalse(appointment.opportunity_id)
        # Trigger confirm via write method
        appointment.write({'state': 'confirmed'})
        # Verify opportunity was linked and created during write() method
        self.assertTrue(appointment.opportunity_id)
