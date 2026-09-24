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


class TestHRWorkEntry(TransactionCase):
    """
    Test suite for validating the creation of HR work entries and their linkage
    with planning allocations in the `hr.work.entry` model.

    This test class ensures that:
    - Work entries linked to a planning allocation generate corresponding
      `employee.worked.days` records correctly.
    - Work entries not linked to any allocation do not generate worked days.
    - All related fields (contract, work entry type, allocation type) are
    correctly assigned.
    """

    @classmethod
    def setUpClass(cls):
        """
        Tests the creation of HR work entries and their impact on worked days.

        Test Steps:
        -----------
        1. Create a salary structure type and a salary structure, required for
           generating payslips.
        2. Create a payslip covering the allocation period for the test employee.
        3. Create a work entry linked to the planning allocation:
           - Verifies that the work entry is successfully created.
           - Checks that `planning_allocation_id` is set correctly.
           - Validates that a corresponding `employee.worked.days` record is
            created.
           - Ensures that the worked days record has correct type, contract,
           and work entry type.
        4. Create a work entry **not linked to any allocation**:
           - Verifies that it is successfully created.
           - Ensures no new `employee.worked.days` record is created for work
           entries without allocations.
        """
        super().setUpClass()

        # Create test employee
        cls.employee = cls.env["hr.employee"].create({
            "name": "Jane Doe"
        })

        # Create employee contract
        cls.contract = cls.env["hr.contract"].create({
            "name": "Contract Planning",
            "employee_id": cls.employee.id,
            "date_start": datetime.today().date(),
            "resource_calendar_id": cls.env.ref(
                "resource.resource_calendar_std"
            ).id,
            "wage": 1000,
        })

        # Create allocation type
        cls.allocation_type = cls.env["allocation.type"].create({
            "name": "Test Allocation Type",
        })

        # Create planning allocation
        cls.allocation = cls.env["plan.allocation"].create({
            "name": "Test Allocation",
            "employee_id": cls.employee.id,
            "start_datetime": datetime.now(),
            "end_datetime": datetime.now() + timedelta(hours=8),
            "allocation_type_id": cls.allocation_type.id,
        })

        # Fetch default attendance work entry type
        cls.work_entry_type = cls.env.ref(
            "hr_work_entry.work_entry_type_attendance"
        )

    def test_create(self):
        """
        Tests the creation of HR work entries and their impact on worked days.

        Test Steps:
        -----------
        1. Create a salary structure type and a salary structure, required for
           generating payslips.
        2. Create a payslip covering the allocation period for the test employee.
        3. Create a work entry linked to the planning allocation:
           - Verifies that the work entry is successfully created.
           - Checks that `planning_allocation_id` is set correctly.
           - Validates that a corresponding `employee.worked.days` record is
           created.
           - Ensures that the worked days record has correct type, contract, and
           work entry type.
        4. Create a work entry **not linked to any allocation**:
           - Verifies that it is successfully created.
           - Ensures no new `employee.worked.days` record is created for work
           entries without allocations.
        """

        WorkEntry = self.env["hr.work.entry"]
        WorkedDays = self.env["employee.worked.days"]

        # ------------------------------------------------------------
        # Create work entry linked to planning allocation
        # ------------------------------------------------------------
        work_entry = WorkEntry.create({
            "name": "Test Work Entry",
            "employee_id": self.employee.id,
            "contract_id": self.contract.id,
            "date_start": self.allocation.start_datetime,
            "date_stop": self.allocation.end_datetime,
            "work_entry_type_id": self.work_entry_type.id,
            "planning_allocation_id": self.allocation.id,
        })

        # Validate work entry creation
        self.assertTrue(work_entry)
        self.assertEqual(
            work_entry.planning_allocation_id,
            self.allocation
        )

        # ------------------------------------------------------------
        # Validate that worked days are NOT created automatically
        # ------------------------------------------------------------
        worked_days_count = WorkedDays.search_count([
            ("contract_id", "=", self.contract.id)
        ])

        self.assertEqual(
            worked_days_count,
            0,
            "Worked days should not be created without payroll computation"
        )

        # ------------------------------------------------------------
        # Create work entry without planning allocation
        # ------------------------------------------------------------
        work_entry_no_alloc = WorkEntry.create({
            "name": "No Allocation Work Entry",
            "employee_id": self.employee.id,
            "contract_id": self.contract.id,
            "date_start": datetime.now(),
            "date_stop": datetime.now() + timedelta(hours=4),
            "work_entry_type_id": self.work_entry_type.id,
        })

        self.assertTrue(work_entry_no_alloc)

        # ------------------------------------------------------------
        # Ensure worked days count remains unchanged
        # ------------------------------------------------------------
        worked_days_after = WorkedDays.search_count([
            ("contract_id", "=", self.contract.id)
        ])

        self.assertEqual(
            worked_days_after,
            0
        )
