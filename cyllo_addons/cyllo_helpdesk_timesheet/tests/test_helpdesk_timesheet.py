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


class TestHelpdeskTimesheet(TransactionCase):
    """
    Test suite for verifying the integration of timesheets
    with the Cyllo Helpdesk module.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Team = cls.env['helpdesk.team']
        cls.Ticket = cls.env['helpdesk.ticket']
        cls.AnalyticLine = cls.env['account.analytic.line']
        cls.Employee = cls.env['hr.employee']
        cls.Project = cls.env['project.project']
        cls.Partner = cls.env['res.partner']

        cls.customer = cls.Partner.create({'name': 'Test Customer'})
        cls.employee = cls.Employee.create({'name': 'Test Employee'})
        cls.project = cls.Project.create({'name': 'Test Support Project'})

        # Create helpdesk teams
        cls.team_with_timesheet = cls.Team.create({
            'name': 'Timesheet Team',
            'use_timesheet': True,
        })
        cls.team_without_timesheet = cls.Team.create({
            'name': 'No Timesheet Team',
            'use_timesheet': False,
        })

    def test_01_timesheet_bool_related_field(self):
        """ Test that timesheet_bool reflects team settings correctly """
        ticket_1 = self.Ticket.create({
            'name': 'Ticket 1',
            'team_id': self.team_with_timesheet.id,
            'customer_id': self.customer.id,
        })
        self.assertTrue(ticket_1.timesheet_bool)

        ticket_2 = self.Ticket.create({
            'name': 'Ticket 2',
            'team_id': self.team_without_timesheet.id,
            'customer_id': self.customer.id,
        })
        self.assertFalse(ticket_2.timesheet_bool)

        # Toggle team setting and check related field update
        self.team_with_timesheet.use_timesheet = False
        self.assertFalse(ticket_1.timesheet_bool)

        self.team_with_timesheet.use_timesheet = True
        self.assertTrue(ticket_1.timesheet_bool)

    def test_02_analytic_line_ticket_link(self):
        """ Test linking analytic line to helpdesk ticket """
        ticket = self.Ticket.create({
            'name': 'Timesheet Ticket',
            'team_id': self.team_with_timesheet.id,
            'customer_id': self.customer.id,
        })

        # Create analytic line linked to ticket
        line = self.AnalyticLine.create({
            'name': 'Debugging helpdesk issue',
            'ticket_id': ticket.id,
            'unit_amount': 2.5,
            'employee_id': self.employee.id,
            'project_id': self.project.id,
        })

        self.assertEqual(line.ticket_id, ticket)
        self.assertIn(line, ticket.timesheet_ids)

    def test_03_ticket_timesheets_one2many(self):
        """ Test timesheet_ids one2many relationship on helpdesk.ticket """
        ticket = self.Ticket.create({
            'name': 'Multi Timesheet Ticket',
            'team_id': self.team_with_timesheet.id,
            'customer_id': self.customer.id,
        })

        line_1 = self.AnalyticLine.create({
            'name': 'Initial investigation',
            'ticket_id': ticket.id,
            'unit_amount': 1.0,
            'employee_id': self.employee.id,
            'project_id': self.project.id,
        })

        line_2 = self.AnalyticLine.create({
            'name': 'Resolving and verifying fix',
            'ticket_id': ticket.id,
            'unit_amount': 3.0,
            'employee_id': self.employee.id,
            'project_id': self.project.id,
        })

        self.assertEqual(len(ticket.timesheet_ids), 2)
        self.assertEqual(ticket.timesheet_ids, line_1 | line_2)
