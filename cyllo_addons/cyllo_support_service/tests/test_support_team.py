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
from odoo import Command
from odoo.tests.common import TransactionCase

class TestSupportServiceTeam(TransactionCase):
    """
    Test cases for 'support.service.team' model, focusing on team statistics
    and automated project management.
    """

    def setUp(self):
        """
        Setup test environment for support team functionality tests.
        """
        super(TestSupportServiceTeam, self).setUp()
        self.Ticket = self.env['support.service.ticket']
        self.Team = self.env['support.service.team']
        self.Partner = self.env['res.partner']
        self.User = self.env['res.users']

        self.manager_user = self.User.create({
            'name': 'Test Manager Team',
            'login': 'test_manager_team',
            'email': 'manager_team@test.com',
            'groups_id': [Command.set([self.env.ref('cyllo_support_service.group_cyllo_support_service_team_manager').id])]
        })
        self.team = self.Team.create({
            'name': 'Stats Team',
            'manager_id': self.manager_user.id,
            'company_id': self.env.company.id
        })
        self.customer = self.Partner.create({'name': 'Stats Customer'})

    def test_team_stats(self):
        """
        Test the computation of team statistics like open, unassigned, and urgent ticket counts.
        """
        self.Ticket.create({
            'name': 'Open Ticket',
            'team_id': self.team.id,
            'customer_id': self.customer.id,
            'priority': '3'
        })
        self.Ticket.create({
            'name': 'Another Open Ticket',
            'team_id': self.team.id,
            'customer_id': self.customer.id,
            'user_id': self.manager_user.id
        })
        
        self.team._compute_open_count()
        self.team._compute_unassigned_count()
        self.team._compute_urgent_count()
        
        self.assertEqual(self.team.open_count, 2)
        self.assertEqual(self.team.unassigned_count, 1)
        self.assertEqual(self.team.urgent_count, 1)

    def test_project_creation(self):
        """
        Test the automatic creation of a project when timesheet tracking is enabled for a team.
        """
        self.team.is_timesheet = True
        self.team._compute_project_id()
        
        self.assertTrue(self.team.project_id)
        self.assertEqual(self.team.project_id.name, self.team.name)
