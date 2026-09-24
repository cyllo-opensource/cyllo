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
from odoo.exceptions import ValidationError
from .common import TestBudgetManagement
from datetime import datetime, timedelta
from odoo import _


class TestBudgetLines(TestBudgetManagement):
    """Test methods of the Budget Lines"""

    def test_compute_start_date(self):
        # compute start date of a budget line
        self.budget_line01._compute_start_date()
        self.assertEqual(self.budget_line01.start_date,
                         datetime.strptime('29-04-2024', '%d-%m-%Y').date())
        self.assertEqual(self.budget_line01.end_date,
                         datetime.strptime('01-05-2024', '%d-%m-%Y').date())

    def test_compute_theoretical_amount(self):
        # start_date < today < end_date
        self.budget_line02._compute_theoretical_amount()
        self.assertEqual(self.budget_line02.theoretical_amount, 600)
        # start_date < end_date < today
        self.budget_line03._compute_theoretical_amount()
        self.assertEqual(self.budget_line03.theoretical_amount, 1100)
        #  today < start_date < end_date
        self.budget_line04._compute_theoretical_amount()
        self.assertEqual(self.budget_line04.theoretical_amount, 0)

    def test_compute_analytic_account_ids(self):
        # Assert that the analytic_account_ids field is set correctly
        self.budget_line02._compute_analytic_account_ids()
        self.assertEqual(self.budget_line02.analytic_account_ids,
                         self.env['account.analytic.account'].search(
                             [('analytic_account_id', '=', False)]))

    def test_action_budget_configuration(self):
        self.budget_line02.action_budget_configuration()
        # Assert that the check_configuration field is set to True
        self.assertTrue(self.budget_line02.check_configuration)

    def test_action_budget_configuration_view(self):
        result = self.budget_line02.action_budget_configuration_view()
        expected_result = {
            'type': 'ir.actions.act_window',
            'name': _("Budget Lines Configuration"),
            'res_model': 'budget.lines.configuration',
            'view_mode': 'tree',
            'domain': [('budget_line_id', '=', self.budget_line02.id)],
            'context': {},
            'views': [
                (self.budget_line02.env.ref(
                    'cyllo_budget_management.view_budget_lines_configuration_tree').id,
                 'list'),
            ],
        }
        self.assertEqual(result, expected_result)

    def test_start_date_within_budget_dates(self):
        # No validation should raised where start date and end date are within budget dates
        try:
            self.budget_line01._check_start_date()
        except ValidationError as e:
            self.fail(f"Unexpected ValidationError: {e}")
        # start date and end date are beyond budget dates
        with self.assertRaises(ValidationError):
            self.budget_line01.start_date = (
                        self.budget_line01.budget_id.start_date - timedelta(1))
            self.budget_line02._check_start_date()

    def test_onchange_budget_type(self):
        # budget_type= spend
        self.budget_line02.budget_type = 'spend'
        self.budget_line02.planned_amount = 1000
        self.budget_line02._onchange_budget_type()
        self.assertEqual(self.budget_line02.planned_amount, -1000)
        # budget_type= earn
        self.budget_line02.budget_type = 'earn'
        self.budget_line02.planned_amount = -1000
        self.budget_line02._onchange_budget_type()
        self.assertEqual(self.budget_line02.planned_amount, 1000)

    def test_action_view_moves(self):
        # Invoke the action_view_moves method
        result = self.budget_line02.action_view_moves()
        # Assert that the result is a dictionary
        self.assertIsInstance(result, dict)
        # Assert that the result contains the required keys
        self.assertIn('type', result)
        self.assertIn('name', result)
        self.assertIn('res_model', result)
        self.assertIn('domain', result)
        self.assertIn('views', result)
        # with no analytic account
        # Invoke the action_view_moves method
        result = self.budget_line07.action_view_moves()
        # Assert that the result is a dictionary
        self.assertIsInstance(result, dict)
        # Assert that the result contains the required keys
        self.assertIn('type', result)
        self.assertIn('name', result)
        self.assertIn('res_model', result)
        self.assertIn('domain', result)
        self.assertIn('views', result)

    def test_check_account_ids(self):
        # No Validation error should raised where any  account is selected
        try:
            self.budget_line02._check_account_ids()
        except ValidationError:
            self.fail("Unexpected ValidationError raised")
