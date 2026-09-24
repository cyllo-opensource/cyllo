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
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError
from datetime import datetime


class TestTimesheetGrid(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Create a test employee first
        calendar = cls.env['resource.calendar'].search([], limit=1)
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Test Employee',
            'resource_calendar_id': calendar.id
        })

        cls.user = cls.env['res.users'].create({
            'name': 'Test User',
            'login': 'testuser@example.com',
            'email': 'testuser@example.com',
            'employee_ids': [(4, cls.employee.id)]
        })

        # Use existing project or create with SQL to bypass validation
        cls.project = cls.env['project.project'].search([], limit=1)
        if not cls.project:
            # Create project directly in database with billing_type
            cls.env.cr.execute("""
                INSERT INTO project_project (name, billing_type, allow_timesheets, create_uid, write_uid, create_date, write_date)
                VALUES ('Test Project', 'non_billable', true, %s, %s, NOW(), NOW())
                RETURNING id
            """, (cls.env.uid, cls.env.uid))
            project_id = cls.env.cr.fetchone()[0]
            cls.project = cls.env['project.project'].browse(project_id)

        # Create a test task
        cls.task = cls.env['project.task'].create({
            'name': 'Test Task',
            'project_id': cls.project.id
        })

        cls.timesheet_grid = cls.env['timesheet.grid']

    def test_fetch_remaining_hours_empty(self):
        result = self.timesheet_grid.fetch_remaining_hours([])
        self.assertEqual(result, [])

    def test_change_hours_backend_create(self):
        js_date = datetime.today().strftime("%d/%m/%Y, %H:%M:%S")

        self.timesheet_grid.change_hours_backend(
            project_id=self.project.id,
            task_id=self.task.id,
            float_value=4.0,
            js_date=js_date,
            employee_id=self.employee.id
        )

        timesheet = self.env['account.analytic.line'].search([
            ('task_id', '=', self.task.id),
            ('employee_id', '=', self.employee.id)
        ])
        self.assertTrue(len(timesheet) >= 1)
        self.assertEqual(timesheet[0].unit_amount, 4.0)

    def test_hours_value_backend(self):
        today = datetime.today()
        js_date = today.strftime("%d/%m/%Y, %H:%M:%S")

        self.env['account.analytic.line'].create({
            'task_id': self.task.id,
            'project_id': self.project.id,
            'employee_id': self.employee.id,
            'date': today.date(),
            'unit_amount': 3.5,
            'name': 'Test Timesheet'
        })

        value = self.timesheet_grid.hours_value_backend(
            project_id=self.project.id,
            task_id=self.task.id,
            employee_id=self.employee.id,
            date=js_date
        )
        self.assertEqual(value, 3.5)

    def test_overtime_work(self):
        hours = self.timesheet_grid.overtime_work(self.user.id)
        self.assertGreater(hours, 0)

    def test_timesheet_duration(self):
        settings = self.timesheet_grid.timesheet_duration()
        self.assertIsInstance(settings, dict)

    def test_day_hour_check(self):
        is_day = self.timesheet_grid.day_hour_check()
        self.assertIsInstance(is_day, bool)