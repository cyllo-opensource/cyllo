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
from odoo.tests import tagged, TransactionCase


@tagged('post_install', '-at_install')
class TestHelpdeskHR(TransactionCase):
    """Test suite for the Cyllo Helpdesk HR integration features."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Create res.users for members
        cls.user_a = cls.env['res.users'].create({
            'name': 'Tech Agent A',
            'login': 'agent_a',
            'email': 'agent_a@test.com',
            'groups_id': [(6, 0, [cls.env.ref('cyllo_helpdesk.cyllo_helpdesk_user').id])],
        })
        cls.user_b = cls.env['res.users'].create({
            'name': 'Tech Agent B',
            'login': 'agent_b',
            'email': 'agent_b@test.com',
            'groups_id': [(6, 0, [cls.env.ref('cyllo_helpdesk.cyllo_helpdesk_user').id])],
        })

        # Create hr.employees linked to users
        cls.employee_a = cls.env['hr.employee'].create({
            'name': 'Employee Agent A',
            'user_id': cls.user_a.id,
        })
        cls.employee_b = cls.env['hr.employee'].create({
            'name': 'Employee Agent B',
            'user_id': cls.user_b.id,
        })

        # Create skills levels
        cls.levels = cls.env['hr.skill.level'].create([{
            'name': f'Level {x}',
            'level_progress': x * 10,
        } for x in range(1, 4)])

        # Create skill type
        cls.skill_type = cls.env['hr.skill.type'].create({
            'name': 'Programming Languages',
            'skill_level_ids': cls.levels.ids,
        })

        # Create skills
        cls.skill_python = cls.env['hr.skill'].create({
            'name': 'Python',
            'skill_type_id': cls.skill_type.id,
        })
        cls.skill_sql = cls.env['hr.skill'].create({
            'name': 'SQL',
            'skill_type_id': cls.skill_type.id,
        })

        # Link skills to employees
        # Employee A has Python and SQL
        cls.env['hr.employee.skill'].create({
            'employee_id': cls.employee_a.id,
            'skill_id': cls.skill_python.id,
            'skill_level_id': cls.levels[0].id,
            'skill_type_id': cls.skill_type.id,
        })
        cls.env['hr.employee.skill'].create({
            'employee_id': cls.employee_a.id,
            'skill_id': cls.skill_sql.id,
            'skill_level_id': cls.levels[0].id,
            'skill_type_id': cls.skill_type.id,
        })

        # Employee B has only Python
        cls.env['hr.employee.skill'].create({
            'employee_id': cls.employee_b.id,
            'skill_id': cls.skill_python.id,
            'skill_level_id': cls.levels[0].id,
            'skill_type_id': cls.skill_type.id,
        })

        # Create Helpdesk Team with skill assignment method
        cls.team = cls.env['helpdesk.team'].create({
            'name': 'Tech Support Team',
            'assignment_method': 'skill',
            'member_ids': [(6, 0, [cls.user_a.id, cls.user_b.id])],
        })

    def test_assignment_by_specific_skill(self):
        """Test that ticket is assigned to the agent matching the required skill."""
        # Create a ticket requiring SQL skill (Only Agent A has it)
        ticket = self.env['helpdesk.ticket'].create({
            'name': 'Database Issue',
            'team_id': self.team.id,
            'skill_ids': [(6, 0, [self.skill_sql.id])],
        })
        self.assertEqual(ticket.user_id.id, self.user_a.id, 
                         "Ticket requiring SQL should be assigned to Agent A.")

    def test_assignment_by_workload_fallback(self):
        """Test that ticket with shared skills is assigned to agent with lower workload."""
        # Create an unclosed ticket assigned to Agent A to increase workload
        ticket_a = self.env['helpdesk.ticket'].create({
            'name': 'Existing Ticket for A',
            'team_id': self.team.id,
            'user_id': self.user_a.id,
        })

        # Create a new ticket requiring Python skill (Both Agent A and B have it)
        # Agent B has 0 tickets, Agent A has 1. It should go to Agent B.
        ticket_b = self.env['helpdesk.ticket'].create({
            'name': 'Python Script Bug',
            'team_id': self.team.id,
            'skill_ids': [(6, 0, [self.skill_python.id])],
        })
        self.assertEqual(ticket_b.user_id.id, self.user_b.id, 
                         "Ticket requiring Python should be assigned to Agent B (lowest workload).")

    def test_onchange_team_and_skills(self):
        """Test that onchange triggers skill assignment correctly."""
        # Create a ticket with no team or skills
        ticket = self.env['helpdesk.ticket'].new({
            'name': 'Draft Ticket',
        })
        ticket.user_id = False
        self.assertFalse(ticket.user_id)

        # Set team and skill
        ticket.team_id = self.team.id
        ticket.skill_ids = [(6, 0, [self.skill_sql.id])]

        # Call onchange
        ticket._onchange_team_id_assignment()
        self.assertEqual(ticket.user_id.id, self.user_a.id, 
                         "Onchange should assign the ticket based on skills.")
