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
from odoo.tests.common import TransactionCase
from odoo import fields

class TestProjectTaskPlanAllocation(TransactionCase):
    """
    Test cases for project task allocation planning, covering count computation,
    view actions, and wizard initialization.
    """

    @classmethod
    def setUpClass(cls):
        """
        Setup class-level test data for project task allocation tests.
        """
        super().setUpClass()

        cls.Project = cls.env['project.project']
        cls.Task = cls.env['project.task']
        cls.Employee = cls.env['hr.employee']
        cls.User = cls.env['res.users']
        cls.PlanAllocation = cls.env['plan.allocation']
        cls.AllocationType = cls.env['allocation.type']

        cls.user = cls.User.create({
            'name': 'Test User',
            'login': 'test_user_alloc',
            'email': 'test_user_alloc@example.com',
        })

        cls.employee = cls.Employee.create({
            'name': 'Test Employee',
            'user_id': cls.user.id,
        })

        cls.allocation_type = cls.AllocationType.create({
            'name': 'Test Allocation Type',
        })

        cls.project = cls.Project.create({
            'name': 'Test Project',
            'allow_billable': False,
            'billing_type': 'not_billable'
        })

        cls.task = cls.Task.create({
            'name': 'Test Task',
            'project_id': cls.project.id,
            'user_ids': [(6, 0, [cls.user.id])],
            'date_assign': fields.Datetime.now(),
            'date_deadline': fields.Datetime.now(),
        })

    def test_allocation_count_compute(self):
        """
        Test the computation of the allocation count on the task.
        """
        self.PlanAllocation.create({
            'task_id': self.task.id,
            'employee_id': self.employee.id,
            'user_id': self.user.id,
            'allocation_type_id': self.allocation_type.id,
            'start_datetime': fields.Datetime.now(),
            'end_datetime': fields.Datetime.now() + timedelta(hours=1),
        })

        self.task.invalidate_recordset(['plan_allocation_ids'])

        self.assertEqual(
            self.task.allocation_count,
            1,
            "Allocation count should be 1 after creating allocation"
        )

    def test_action_view_allocations(self):
        """
        Test the action that opens the view for allocations related to the task.
        """
        action = self.task.action_view_allocations()

        self.assertEqual(action['res_model'], 'plan.allocation')
        self.assertEqual(action['view_mode'], 'tree')
        self.assertIn(('task_id', '=', self.task.id), action['domain'])

    def test_action_plan_task_allocations(self):
        """
        Test the action that opens the wizard to plan task allocations.
        """
        action = self.task.action_plan_task_allocations()
        context = action.get('context', {})

        self.assertEqual(action['res_model'], 'project.plan.allocation')
        self.assertEqual(action['target'], 'new')
        self.assertEqual(context.get('default_task_id'), self.task.id)
        self.assertEqual(context.get('default_project_id'), self.project.id)
        self.assertIn(self.employee.id, context.get('default_employee_ids'))

    def test_project_task_allocation_editability(self):
        """
        Test that project_id and task_id are editable and synchronize correctly.
        """
        # Create allocation with project only
        alloc = self.PlanAllocation.create({
            'project_id': self.project.id,
            'employee_id': self.employee.id,
            'user_id': self.user.id,
            'allocation_type_id': self.allocation_type.id,
            'start_datetime': fields.Datetime.now(),
            'end_datetime': fields.Datetime.now() + timedelta(hours=1),
        })
        self.assertEqual(alloc.project_id, self.project)
        self.assertFalse(alloc.task_id)

        # Set task_id and check that project_id gets updated
        alloc.task_id = self.task
        self.assertEqual(alloc.project_id, self.project)

        # Simulate changing project_id via onchange - should clear task_id if project differs
        new_project = self.Project.create({'name': 'Another Project'})
        alloc.project_id = new_project
        alloc._onchange_project_id()
        self.assertFalse(alloc.task_id)

