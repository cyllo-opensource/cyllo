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
import calendar
from odoo.exceptions import ValidationError
from .common import TestBudgetManagement
from datetime import datetime, timedelta
from odoo import fields


class TestBudgetBudget(TestBudgetManagement):
    """Test methods of the Budget"""

    def test_compute_end_date(self):
        self.budget01._compute_end_date()
        expected_end_date_01 = datetime.strptime('29-04-2024',
                                                 '%d-%m-%Y').date()
        self.assertEqual(self.budget01.end_date, expected_end_date_01)
        self.budget02._compute_end_date()
        expected_end_date_02 = datetime.strptime('05-05-2024',
                                                 '%d-%m-%Y').date()
        self.assertEqual(self.budget02.end_date, expected_end_date_02)
        self.budget03._compute_end_date()
        expected_end_date_03 = datetime.strptime('28-05-2024',
                                                 '%d-%m-%Y').date()
        self.assertEqual(self.budget03.end_date, expected_end_date_03)
        self.budget04._compute_end_date()
        expected_end_date_04 = datetime.strptime('29-04-2025',
                                                 '%d-%m-%Y').date()
        self.assertEqual(self.budget04.end_date, expected_end_date_04)

    def test_action_compute_budget(self):
        self.budget01.action_compute_budget()
        self.assertEqual(self.budget_line01.achievement, 0.5)
        self.budget09.success_rate = 2
        self.budget09.action_compute_budget()
        self.assertEqual(self.budget_line091.stage, 'success')
        self.assertEqual(self.budget_line092.stage, 'success')
        self.assertEqual(self.budget_line093.stage, 'fail')
        self.assertEqual(self.budget_line094.stage, 'fail')

    def test_action_confirm_budget(self):
        self.budget01.action_confirm_budget()
        self.assertEqual(self.budget01.state, 'confirm')

    def test_action_approve_budget(self):
        self.budget01.action_approve_budget()
        self.assertEqual(self.budget01.state, 'approve')

    def test_action_cancel_budget(self):
        self.budget01.action_cancel_budget()
        self.assertEqual(self.budget01.state, 'cancel')

    def test_action_reset_to_draft(self):
        self.budget01.action_reset_to_draft()
        self.assertEqual(self.budget01.state, 'draft')

    def test_action_reject_budget(self):
        self.budget01.state = 'confirm'
        self.budget01.action_reject_budget()
        self.assertEqual(self.budget01.state, 'reject')

    def test_check_due_date(self):
        self.budget09.due_date = self.budget09.end_date + timedelta(days=1)
        self.budget09._check_due_date()
        self.budget09.due_date = self.budget09.end_date
        self.budget09._check_due_date()
        #  due_date < end_date
        with self.assertRaises(ValidationError):
            self.budget09.due_date = self.budget09.end_date + timedelta(days=-1)
            self.budget09._check_due_date()

    def test_check_start_date(self):
        # end_date > start_date
        try:
            self.budget09._check_start_date()
        except ValidationError:
            self.fail("Validation Error should not be raised")
        # end_date = start_date
        try:
            self.budget09.end_date = self.budget09.start_date
            self.budget09._check_start_date()
        except ValidationError:
            self.fail("Validation Error should not be raised")
        # end_date < start_date
        with self.assertRaises(ValidationError):
            self.budget09.end_date = self.budget09.start_date + timedelta(-1)
            self.budget09._check_start_date()

    def test_onchange_end_date(self):
        # end date changes where period_type = 'month'
        self.budget03.period_type = 'month'
        self.budget03.end_date = fields.Date.today()
        self.budget03._onchange_end_date()
        self.assertEqual(self.budget03.start_date,
                         self.budget03.end_date - timedelta(
                             calendar.monthrange(self.budget03.end_date.year,
                                                 self.budget03.end_date.month)[
                                 1] - 1))
        # end date changes where period_type = 'day'
        self.budget01.period_type = 'day'
        self.budget01.end_date = fields.Date.today()
        self.budget01._onchange_end_date()
        self.assertEqual(self.budget01.start_date, self.budget01.end_date)
        # end date changes where period_type = 'false'
        self.budget01.period_type = False
        self.budget01.end_date = fields.Date.today()
        self.budget01._onchange_end_date()
        self.assertEqual(self.budget01.start_date, self.budget01.end_date)
        # end date changes where period_type = 'week'
        self.budget01.period_type = 'week'
        self.budget01.end_date = fields.Date.today()
        self.budget01._onchange_end_date()
        self.assertEqual(self.budget01.start_date,
                         self.budget01.end_date - timedelta(6))
        # end date changes where period_type = 'month'
        self.budget03.period_type = 'month'
        self.budget03.end_date = fields.Date.today()
        self.budget03._onchange_end_date()
        end_date_month = timedelta(
            calendar.monthrange(self.budget03.end_date.year,
                                self.budget03.end_date.month)[1])
        if timedelta(self.budget03.end_date.day) < end_date_month:
            end_date_previous_month = (
                        self.budget03.end_date.replace(day=1) - timedelta(
                    1)).month
            expected_start_date = self.budget03.end_date - timedelta(
                calendar.monthrange(self.budget03.end_date.year,
                                    end_date_previous_month)[1] - 1)
        else:
            expected_start_date = self.budget03.end_date - timedelta(
                calendar.monthrange(self.budget03.end_date.year,
                                    self.budget03.end_date.month)[1] - 1)
        self.assertEqual(self.budget03.start_date, expected_start_date)

    def test_onchange_start_date(self):
        # Set the values for the start_date and end_date fields
        self.budget05.end_date = fields.Date.today() + timedelta(days=5)
        # Invoke the _onchange_start_date method
        self.budget05._onchange_start_date()
        # Assert that the budget line dates are updated accordingly
        self.assertEqual(self.budget_line02.start_date,
                         fields.Date.today() + timedelta(days=-5))
        self.assertEqual(self.budget_line02.end_date,
                         fields.Date.today() + timedelta(days=5))
        self.assertEqual(self.budget_line07.start_date,
                         fields.Date.today() + timedelta(days=-5))
        self.assertEqual(self.budget_line07.end_date,
                         fields.Date.today() + timedelta(days=5))
