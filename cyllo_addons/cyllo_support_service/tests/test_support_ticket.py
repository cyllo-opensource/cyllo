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
from datetime import timedelta
from unittest.mock import patch, MagicMock
from odoo import fields, Command
from odoo.tests.common import TransactionCase

class TestSupportServiceTicket(TransactionCase):
    """
    Test cases for 'support.service.ticket' model, covering ticket lifecycle,
    assignment, SLA monitoring, and billing.
    """

    def setUp(self):
        """
        Setup test data for support ticket lifecycle tests.
        """
        super(TestSupportServiceTicket, self).setUp()
        self.Ticket = self.env['support.service.ticket']
        self.Team = self.env['support.service.team']
        self.Partner = self.env['res.partner']
        self.User = self.env['res.users']
        self.Stage = self.env['support.service.stage']

        self.customer = self.Partner.create({'name': 'Test Customer', 'email': 'customer@test.com'})
        self.manager_user = self.User.create({
            'name': 'Test Manager',
            'login': 'test_manager',
            'email': 'manager@test.com',
            'groups_id': [Command.set([self.env.ref('cyllo_support_service.group_cyllo_support_service_team_manager').id])]
        })
        self.team = self.Team.create({
            'name': 'Test Team',
            'manager_id': self.manager_user.id,
            'company_id': self.env.company.id
        })
        
        self.stage_new = self.env.ref('cyllo_support_service.support_service_stage_new')
        self.stage_in_progress = self.env.ref('cyllo_support_service.support_service_stage_in_progress')
        self.stage_solved = self.env.ref('cyllo_support_service.support_service_stage_solved')

    def test_ticket_creation(self):
        """
        Test ticket creation and validation of default field values.
        """
        ticket = self.Ticket.create({
            'name': 'Test Ticket',
            'customer_id': self.customer.id,
            'team_id': self.team.id
        })
        self.assertTrue(ticket.ticket != 'New')
        self.assertEqual(ticket.stage_id, self.stage_new)

    def test_action_assign_ticket(self):
        """
        Test assigning a ticket to a user and verifying stage transition.
        """
        user = self.User.create({
            'name': 'Test User',
            'login': 'test_user',
            'email': 'user@test.com',
        })
        self.env['hr.employee'].create({'name': 'Admin Employee', 'user_id': self.env.user.id})
        self.env['hr.employee'].create({'name': 'Test Employee', 'user_id': user.id})
        
        ticket = self.Ticket.create({
            'name': 'Assign Ticket',
            'customer_id': self.customer.id,
            'team_id': self.team.id,
            'user_id': user.id,
            'deadline': fields.Datetime.now() + timedelta(days=1)
        })

        with patch('odoo.addons.mail.models.mail_template.MailTemplate.send_mail'):
            ticket.action_assign_ticket()
            self.assertEqual(ticket.stage_id, self.stage_in_progress)

    def test_ticket_lifecycle(self):
        """
        Test various ticket actions including pausing, resuming, and closing.
        """
        ticket = self.Ticket.create({
            'name': 'Lifecycle Ticket',
            'customer_id': self.customer.id,
            'team_id': self.team.id
        })
        
        ticket.action_pause_ticket(ticket.id)
        self.assertEqual(ticket.stage_id, self.env.ref('cyllo_support_service.support_service_stage_on_hold'))
        
        ticket.action_resume_ticket(ticket.id)
        self.assertEqual(ticket.stage_id, self.stage_in_progress)
        
        with patch('odoo.addons.mail.models.mail_template.MailTemplate.send_mail'):
            ticket.user_id = self.manager_user.id
            ticket.action_done_ticket()
            self.assertEqual(ticket.stage_id, self.stage_solved)

    def test_compute_is_failed(self):
        """
        Test the computation of failed SLA based on deadline violation.
        """
        ticket = self.Ticket.create({
            'name': 'Failed Ticket',
            'customer_id': self.customer.id,
            'team_id': self.team.id,
            'deadline': fields.Datetime.now() - timedelta(days=1)
        })
        ticket._compute_is_failed()
        self.assertTrue(ticket.is_failed)
        
        ticket.deadline = fields.Datetime.now() + timedelta(days=1)
        ticket._compute_is_failed()
        self.assertFalse(ticket.is_failed)

    def test_invoice_creation(self):
        """
        Test the generation of a customer invoice based on ticket timesheets.
        """
        original_registry_getitem = self.env.registry.__getitem__
        
        def mock_registry_getitem(registry_self, model_name):
            if model_name == 'account.fiscal.year':
                mock_model = MagicMock()
                mock_model._name = 'account.fiscal.year'
                return mock_model
            return original_registry_getitem(model_name)
        
        self.env['product.product'].create({'name': self.team.name, 'detailed_type': 'service'})
        
        ticket = self.Ticket.create({
            'name': 'Invoice Ticket',
            'customer_id': self.customer.id,
            'team_id': self.team.id,
        })
        
        employee = self.env['hr.employee'].create({'name': 'Employee', 'hourly_cost': 50})
        self.env['account.analytic.line'].create({
            'name': 'Work',
            'ticket_id': ticket.id,
            'unit_amount': 2,
            'employee_id': employee.id,
            'project_id': self.team.project_id.id or self.env['project.project'].create({'name': 'Test Project'}).id
        })
        
        with patch.object(self.env.registry.__class__, '__getitem__', mock_registry_getitem):
            res = ticket.sudo().action_create_invoice()
        
        self.assertEqual(res['res_model'], 'account.move')
        invoice = self.env['account.move'].browse(res['res_id'])
        self.assertEqual(invoice.partner_id, self.customer)
        self.assertEqual(invoice.invoice_line_ids[0].quantity, 2)
        self.assertEqual(invoice.invoice_line_ids[0].price_unit, 50)
