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


class TestAccountMoveLine(TestBudgetManagement):
    """Test methods of the Account Move Lines """

    def test_check_analytic_distribution(self):
        # Without giving Analytical Distribution
        move_line01 = self.env['account.move.line'].create({
            'product_id': self.product01.id,
            'move_id': self.account_move01.id,
            'amount_residual_currency': 100,
        })
        try:
            move_line01._check_analytic_distribution()
        except ValidationError:
            self.fail("Unexpected ValidationError raised")
        # With giving valid Analytical Distribution
        move_line02 = self.env['account.move.line'].create({
            'product_id': self.product01.id,
            'move_id': self.account_move01.id,
            'amount_residual_currency': 100,
            'analytic_distribution': {
                self.analytic01.id: 100
            }
        })
        try:
            move_line02._check_analytic_distribution()
        except ValidationError:
            self.fail("Unexpected ValidationError raised")
        # giving Invalid Analytical Distributions
        with self.assertRaises(ValidationError):
            move_line03 = self.env['account.move.line'].create({
                'product_id': self.product01.id,
                'move_id': self.account_move01.id,
                'amount_residual_currency': 100,
                'analytic_distribution': {
                    self.analytic01.id: 50,
                    self.analytic02.id: 50,
                }
            })
            move_line03._check_analytic_distribution()
