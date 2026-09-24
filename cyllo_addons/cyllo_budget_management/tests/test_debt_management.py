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
from datetime import timedelta


class TestDebtManagement(TestBudgetManagement):
    """Test methods of the Debt Management class."""

    def test_action_confirm_debt(self):
        # Confirm Debt, Return Views
        result = self.debt_01.action_confirm_debt()
        expected_result = {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'debt.payback.wizard',
            'name': 'Payment Confirmation',
            'context': self.env.context,
            'views': [[self.env.ref(
                'cyllo_budget_management.view_debt_payback_wizard_confirm_form').id,
                       'form']],
            'target': 'new'
        }
        self.assertEqual(result, expected_result)

    def test_action_cancel_debt(self):
        self.debt_02.action_cancel_debt()
        self.assertEqual(self.debt_02.state, 'cancel')

    def test_onchange_payback_period(self):
        self.debt_03._onchange_payback_period()
        self.assertEqual(self.debt_03.payback_date,
                         self.debt_03.date + timedelta(7))
        self.debt_04._onchange_payback_period()
        self.assertEqual(self.debt_04.payback_date,
                         self.debt_04.date + timedelta(30))

    def testaction_view_payments(self):
        # returns the payment view
        result = self.debt_01.action_view_payments()
        # Assert the result
        expected_result = {
            'type': 'ir.actions.act_window',
            'name': 'Payments',
            'res_model': 'account.payment',
            'domain': [('ref', 'ilike', 'Debt 01')],
            'views': [[False, 'tree'], [False, 'form']],
        }
        self.assertEqual(result, expected_result)

    def test_check_payback_date(self):
        # payback date > date
        try:
            self.debt_01._check_payback_date()
        except ValidationError:
            self.fail("Validation Error raised unexpectedly")
            # Assert that no exception was raised
        self.assertTrue(True)
        # payback date = date
        try:
            self.debt_01.payback_date = self.debt_01.date
            self.debt_01._check_payback_date()
        except ValidationError:
            self.fail("Validation Error raised unexpectedly")
        # Assert that no exception was raised
        self.assertTrue(True)
        # payback_date < date
        # Invoke the _check_payback_date method
        with self.assertRaises(ValidationError):
            self.debt_01.payback_date = '2021-01-01'
            self.debt_01._check_payback_date()
