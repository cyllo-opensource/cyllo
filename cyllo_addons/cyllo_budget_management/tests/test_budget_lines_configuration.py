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


class TestBudgetLinesConfiguration(TestBudgetManagement):
    """Test methods of the Budget Lines Configurator"""

    def test_onchange_amount(self):
        # with type  as 'amount' and given amount as 500 where the budget type is Earn
        self.budget_line_conf01.type = 'amount'
        self.budget_line_conf01.amount = 550
        self.budget_line_conf01._onchange_amount()
        # Check the results
        self.assertEqual(self.budget_line_conf01.amount, 550)
        self.assertEqual(self.budget_line_conf01.percentage, 50)
        # Change the type into 'percentage'  invoke the method again
        self.budget_line_conf01.type = 'percentage'
        self.budget_line_conf01.percentage = 70
        self.budget_line_conf01._onchange_amount()
        # Check the updated results
        self.assertEqual(self.budget_line_conf01.amount, 770)
        self.assertEqual(self.budget_line_conf01.percentage, 70)
        # with type  as 'amount' and given amount as -100 where the budget type is Spend
        self.budget_line_conf03.type = 'amount'
        self.budget_line_conf03.amount = -100
        self.budget_line_conf03._onchange_amount()
        # Check the results
        self.assertEqual(self.budget_line_conf03.amount, -100)
        self.assertEqual(self.budget_line_conf03.percentage, 10)
        # Change the type  into percentage and invoke the method again
        self.budget_line_conf03.type = 'percentage'
        self.budget_line_conf03.percentage = 20
        self.budget_line_conf03._onchange_amount()
        # Check the updated results
        self.assertEqual(self.budget_line_conf03.amount, -200)
        self.assertEqual(self.budget_line_conf03.percentage, 20)

    def test_check_amount(self):
        # Set the amount and percentage
        self.budget_line_conf01.amount = 550
        self.budget_line_conf01.percentage = 50
        # No validation error should be raised
        self.budget_line_conf01._check_amount()
        # Call the method and assert that a validation error is raised
        with self.assertRaises(ValidationError):
            # Set the amount and percentage that is greater than the planned amount
            self.budget_line_conf01.amount = 1210
            self.budget_line_conf01.percentage = 110
            self.budget_line_conf01._check_amount()
