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


class TestPlanAllocation(TransactionCase):
    """
    Test class for PlanAllocation model extension that automatically creates,
    updates,
    and deletes linked HR Work Entries when plan allocations are created,
    updated, or removed.
    """
    @classmethod
    def setUpClass(cls):
        """Set up test data: employee, contract, allocation type, and work
        entry type.
        """
        super().setUpClass()
        cls.employee = cls.env['hr.employee'].create({'name': 'John Doe'})
        cls.work_entry_type = cls.env.ref(
            'hr_work_entry.work_entry_type_attendance')

        today = datetime.today().date()
        cls.contract = cls.env['hr.contract'].create({
            'name': 'Test Contract',
            'employee_id': cls.employee.id,
            'date_start': today - timedelta(days=30),
            'date_end': today + timedelta(days=30),
            'wage': 1000,
            'state': 'open',
            'work_entry_source': 'planning',
            'resource_calendar_id': cls.env.ref(
                'resource.resource_calendar_std').id,
        })
        cls.allocation_type = cls.env['allocation.type'].create({
            'name': 'Test Allocation Type'
        })

    def test_create(self):
        """Creating a plan allocation automatically creates a linked work
         entry."""
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=8)

        allocation = self.env['plan.allocation'].create({
            'name': 'Morning Shift',
            'employee_id': self.employee.id,
            'start_datetime': start_time,
            'end_datetime': end_time,
            'allocation_type_id': self.allocation_type.id,
        })
        work_entries = self.env['hr.work.entry'].search([
            ('planning_allocation_id', '=', allocation.id)
        ])
        self.assertEqual(len(work_entries), 1)
        work_entry = work_entries[0]
        self.assertEqual(work_entry.employee_id, self.employee)
        self.assertEqual(work_entry.contract_id, self.contract)
        self.assertEqual(work_entry.date_start, allocation.start_datetime)
        self.assertEqual(work_entry.date_stop, allocation.end_datetime)

    def test_write(self):
        """Updating a plan allocation updates its linked work entry."""
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=8)

        allocation = self.env['plan.allocation'].create({
            'name': 'Evening Shift',
            'employee_id': self.employee.id,
            'start_datetime': start_time,
            'end_datetime': end_time,
            'allocation_type_id': self.allocation_type.id,
        })
        work_entry_before = self.env['hr.work.entry'].search([
            ('planning_allocation_id', '=', allocation.id)
        ])
        self.assertEqual(len(work_entry_before), 1,
                         "Initial work entry should exist")
        new_start = allocation.start_datetime + timedelta(hours=1)
        new_end = allocation.end_datetime + timedelta(hours=1)
        allocation.write({'start_datetime': new_start, 'end_datetime': new_end})

        work_entry_after = self.env['hr.work.entry'].search([
            ('planning_allocation_id', '=', allocation.id)
        ])
        self.assertEqual(len(work_entry_after), 1,
                         "No new work entry should be created")
        self.assertEqual(work_entry_after.date_start, new_start)
        self.assertEqual(work_entry_after.date_stop, new_end)

    def test_unlink(self):
        """Deleting a plan allocation deletes its linked work entry."""
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=8)
        allocation = self.env['plan.allocation'].create({
            'name': 'Night Shift',
            'employee_id': self.employee.id,
            'start_datetime': start_time,
            'end_datetime': end_time,
            'allocation_type_id': self.allocation_type.id,
        })
        work_entries = self.env['hr.work.entry'].search([
            ('planning_allocation_id', '=', allocation.id)
        ])
        self.assertEqual(len(work_entries), 1,
                         "Work entry should exist before unlink")
        allocation.unlink()
        work_entries_after = self.env['hr.work.entry'].search([
            ('planning_allocation_id', '=', allocation.id)
        ])
        self.assertFalse(work_entries_after,
                         "Work entry should be deleted after unlink")
    def test_generate_related_work_entries_creates_and_updates(self):
        """Manually calling _generate_related_work_entries creates or updates
        work entries."""
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=8)
        allocation = self.env['plan.allocation'].create({
            'name': 'Manual Shift',
            'employee_id': self.employee.id,
            'start_datetime': start_time,
            'end_datetime': end_time,
            'allocation_type_id': self.allocation_type.id,
        })
        allocation._generate_related_work_entries()
        work_entry = self.env['hr.work.entry'].search([
            ('planning_allocation_id', '=', allocation.id)
        ], limit=1)
        self.assertTrue(work_entry, "Work entry should be created manually")
        self.assertEqual(work_entry.date_start, allocation.start_datetime)
        allocation.write({
            'start_datetime': allocation.start_datetime + timedelta(hours=2),
            'end_datetime': allocation.end_datetime + timedelta(hours=2),
        })
        allocation._generate_related_work_entries()
        updated_work_entry = self.env['hr.work.entry'].search([
            ('planning_allocation_id', '=', allocation.id)
        ], limit=1)
        self.assertEqual(updated_work_entry.date_start,
                         allocation.start_datetime)
        self.assertEqual(updated_work_entry.date_stop, allocation.end_datetime)
