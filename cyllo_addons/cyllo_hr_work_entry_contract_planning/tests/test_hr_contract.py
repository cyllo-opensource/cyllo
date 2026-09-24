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

from odoo.tests.common import TransactionCase


class TestHRContract(TransactionCase):
    """
    Test suite for validating the custom `_get_work_entries_values` method
    in the `hr.contract` model when work entries are generated from
    planning allocations.
    """
    @classmethod
    def setUpClass(cls):
        """
        Set up reusable test data for all test cases:
        - Create an employee.
        - Create a contract for the employee with `work_entry_source` set to 'planning'.
        - Create an allocation type.
        - Create a planning allocation linked to the employee and allocation type.
        """
        super().setUpClass()
        cls.employee = cls.env['hr.employee'].create({
            'name': 'John Doe',
        })
        cls.contract = cls.env['hr.contract'].create({
            'name': 'contract Planning',
            'employee_id': cls.employee.id,
            'date_start': datetime.today().date(),
            'resource_calendar_id': cls.env.ref('resource.resource_calendar_std').id,
            'work_entry_source': 'planning',
            'wage': 1000,
        })
        allocation_type = cls.env['allocation.type'].create({
            'name': 'Test Allocation Type',
        })
        cls.allocation = cls.env['plan.allocation'].create({
            'name': 'Test Allocation',
            'employee_id': cls.employee.id,
            'start_datetime': datetime.now(),
            'end_datetime': datetime.now() + timedelta(hours=2),
            'allocation_type_id': allocation_type.id,
        })

    def test_get_work_entries_values(self):
        """
        Validate `_get_work_entries_values` for a contract using planning
         allocations.

        Steps:
        1. Call the method with a date range that includes the allocation.
           → Expect a work entry dictionary to be generated.
        2. Verify the generated values are correctly linked to the employee
           and the planning allocation.
        3. Manually create an `hr.work.entry` for the allocation.
           → Ensure subsequent calls do not generate duplicate values.
        """
        date_start = datetime.now() - timedelta(days=1)
        date_stop = datetime.now() + timedelta(days=1)
        values = self.contract._get_work_entries_values(date_start, date_stop)
        self.assertTrue(values)
        self.assertEqual(values[0]['employee_id'], self.employee.id)
        self.assertEqual(values[0]['planning_allocation_id'], self.allocation.id)
        first_values = self.contract._get_work_entries_values(date_start, date_stop)
        self.assertTrue(first_values)
        self.env['hr.work.entry'].create({
            'name': first_values[0]['name'],
            'employee_id': self.employee.id,
            'contract_id': self.contract.id,
            'date_start': first_values[0]['date_start'],
            'date_stop': first_values[0]['date_stop'],
            'planning_allocation_id': self.allocation.id,
        })
        second_values = self.contract._get_work_entries_values(date_start,
                                                               date_stop)
        self.assertFalse(second_values)
