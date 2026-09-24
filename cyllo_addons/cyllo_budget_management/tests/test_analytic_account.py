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
from .common import TestBudgetManagement


class TestAnalyticAccount(TestBudgetManagement):
    """Test methods of the Analytic Account"""

    def test_compute_parent_ids(self):
        # choosing accounts that has parents
        self.analytic04._compute_parent_ids()
        self.assertIsNotNone(self.analytic04.parent_ids)
        # choosing accounts that has no parents
        self.analytic01._compute_parent_ids()
        self.assertFalse(self.analytic01.parent_ids)

    def test_compute_analytic_account_ids(self):
        # returns the child accounts
        self.analytic01._compute_analytic_account_ids()
        self.assertNotEqual(self.analytic01.analytic_account_ids,
                            self.env['account.analytic.account'])
        # Invoke the _compute_analytic_account_ids method where no child accounts
        self.analytic04._compute_analytic_account_ids()
        # Assert that the analytic_account_ids field is empty
        self.assertEqual(self.analytic04.analytic_account_ids,
                         self.env['account.analytic.account'])

    def test_onchange_analytic_account_id(self):
        # Check if the plan_id is updated with the parent account's plan_id
        self.analytic05._onchange_analytic_account_id()
        self.assertEqual(self.analytic05.plan_id.id, self.analytic01.plan_id.id)
        self.analytic04._onchange_analytic_account_id()
        self.assertEqual(self.analytic04.plan_id.id, self.analytic_plan01.id)

    def test_compute_budget_line_ids(self):
        # Compute budget lines
        self.analytic01._compute_budget_line_ids()
        # Check if budget_line_ids field is set with the computed budget lines
        self.assertIn(self.budget_line01, self.analytic01.budget_line_ids)
        self.assertIn(self.budget_line02, self.analytic01.budget_line_ids)
        # Compute budget lines where the analytic account is not in any budget
        self.analytic05._compute_budget_line_ids()
        # Check if budget_line_ids field is empty
        self.assertEqual(len(self.analytic05.budget_line_ids), 0)
