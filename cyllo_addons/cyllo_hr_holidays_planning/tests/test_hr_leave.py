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
from datetime import datetime, timedelta

from odoo import fields
from odoo.tests.common import TransactionCase


class TestHRLeave(TransactionCase):
    """
    Test suite for validating the integration between HR Leave (`hr.leave`)
    and Planning Allocation (`plan.allocation`).

    This ensures that:
    - Approving a leave automatically creates a linked planning allocation.
    - Refusing a leave deletes the corresponding planning allocation.
    """

    @classmethod
    def setUpClass(cls):
        """
        Set up demo data required for the test cases.

        Creates:
        - An employee (`hr.employee`) for leave requests.
        - An allocation type (`allocation.type`) used to categorize planning.
        - A planning allocation (`plan.allocation`) not linked to a leave yet.
        - A leave type (`hr.leave.type`) with allocation type configured.
        - A leave request (`hr.leave`) for the test employee.
        """
        super().setUpClass()

        cls.employee = cls.env['hr.employee'].create({
            'name': 'Test Employee',
        })

        cls.allocation_type = cls.env['allocation.type'].create({
            'name': 'Test Allocation Type',
        })

        cls.allocation_record = cls.env['plan.allocation'].create({
            'name': 'Test Allocation',
            'allocation_type_id': cls.allocation_type.id,
            'employee_id': cls.employee.id,
            'start_datetime': fields.Datetime.now(),
            'end_datetime': fields.Datetime.now(),
            'leave_id': False,
        })

        cls.leave_type = cls.env['hr.leave.type'].create({
            'name': 'Test Leave Type',
            'requires_allocation': 'no',
            'planning_allocation_type_id': cls.allocation_type.id,
        })

        cls.leave = cls.env['hr.leave'].create({
            'name': 'Vacation Request',
            'holiday_status_id': cls.leave_type.id,
            'employee_id': cls.employee.id,
            'holiday_type': 'employee',
            'request_date_from': datetime.today(),
            'request_date_to': datetime.today() + timedelta(days=2),
            'date_from': datetime.today(),
            'date_to': datetime.today() + timedelta(days=2),
        })

    def test_action_approve_creates_plan_allocation(self):
        """
        Test that approving a leave creates a planning allocation.

        Steps:
        1. Confirm no allocation exists for the leave before approval.
        2. Approve the leave.
        3. Verify that exactly one allocation is created.
        4. Ensure the allocation is correctly linked to:
           - The test employee
           - The configured allocation type
           - The leave request itself
        """
        allocations_before = self.env['plan.allocation'].search(
            [('leave_id', '=', self.leave.id)]
        )
        self.assertFalse(allocations_before)

        self.leave.action_approve()

        allocations_after = self.env['plan.allocation'].search(
            [('leave_id', '=', self.leave.id)]
        )
        self.assertTrue(allocations_after)
        self.assertEqual(len(allocations_after), 1)

        allocation = allocations_after[0]
        self.assertEqual(allocation.employee_id, self.employee)
        self.assertEqual(allocation.allocation_type_id, self.allocation_type)
        self.assertEqual(allocation.leave_id, self.leave)

    def test_action_refuse(self):
        """
        Test that refusing a leave deletes the linked planning allocation.

        Steps:
        1. Approve the leave to generate a planning allocation.
        2. Confirm the allocation exists.
        3. Refuse the leave.
        4. Verify the allocation is deleted.
        """
        self.leave.action_approve()
        allocation_before = self.env['plan.allocation'].search(
            [('leave_id', '=', self.leave.id)]
        )
        self.assertTrue(allocation_before)
        self.leave.action_refuse()
        allocation_after = self.env['plan.allocation'].search(
            [('leave_id', '=', self.leave.id)]
        )
        self.assertFalse(allocation_after)
