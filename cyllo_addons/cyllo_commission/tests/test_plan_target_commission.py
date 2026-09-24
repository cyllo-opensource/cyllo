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
from datetime import date, timedelta

from odoo.tests.common import TransactionCase


class TestCommissionPlanTargetCommission(TransactionCase):
    """

    """
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.company = cls.env.company
        cls.currency = cls.company.currency_id
        cls.team = cls.env['crm.team'].create({'name': ' singlee Team'})
        cls.type= cls.env['commission.type'].create({'name': 'Test Type'})
        cls.plan = cls.env['commission.plan'].create({
            'name': 'Test Plan',
            'company_id': cls.company.id,
            'currency_id': cls.currency.id,
            'type': 'target',
            'team_id': cls.team.id,
            'type_id': cls.type.id,
            'date_from': date.today().replace(month=1, day=1),
            'date_to': date.today().replace(month=12, day=31),
            'commission_amount': 1000.0,
        })
    def test_compute_amount_rate(self):
        """
        Test the _compute_amount_rate method for commission plan targets.
        - When a commission target has a non-zero amount, the rate should be
          calculated as `amount / plan.commission_amount`.
        - When the target amount is zero, the computed rate should also be zero.
        """
        target_commission = self.env['commission.plan.target.commission'].create({
            'plan_id': self.plan.id,
            'amount': 200.0,
            'company_id': self.company.id,
        })
        target_commission._compute_amount_rate()
        self.assertAlmostEqual(target_commission.amount_rate, 0.2, 2)
        target_commission_no_value = self.env['commission.plan.target.commission'].create({
            'plan_id': self.plan.id,
            'amount': 0.0,
            'company_id': self.company.id,
        })
        target_commission_no_value._compute_amount_rate()
        self.assertEqual(target_commission_no_value.amount_rate, 0.0)

    def test_inverse_amount_rate(self):
        """
        Test the inverse method `_inverse_amount_rate`.
        - When a plan has a commission_amount and amount_rate is set,
          the amount should equal (commission_amount * amount_rate).
        - When either commission_amount or amount_rate is zero,
          the amount should default to 0.0.
        """
        target_commission = self.env['commission.plan.target.commission'].create({
            'plan_id': self.plan.id,
            'amount_rate': 0.3,
            'company_id': self.company.id,
        })
        target_commission._inverse_amount_rate()
        self.assertEqual(target_commission.amount, 300.0)
        target_commission_zero_rate = self.env['commission.plan.target.commission'].create({
            'plan_id': self.plan.id,
            'amount_rate': 0.0,
            'company_id': self.company.id,
        })
        target_commission_zero_rate._inverse_amount_rate()
        self.assertEqual(target_commission_zero_rate.amount, 0.0)

        empty_team = self.env['crm.team'].create({'name': 'Empty Team'})
        empty_type= self.env['commission.type'].create({'name': 'empty Type'})
        empty_plan = self.env['commission.plan'].create({
            'name': "Empty Plan",
            'commission_amount': 0.0,
            'company_id': self.company.id,
            'type_id': empty_type.id,
            'team_id': empty_team.id,
            'date_from': date.today().replace(month=1, day=1),
            'date_to': date.today().replace(month=12, day=31),
        })
        target_commission_no_plan_amount = self.env['commission.plan.target.commission'].create({
            'plan_id': empty_plan.id,
            'amount_rate': 0.5,
            'company_id': self.company.id,
        })
        target_commission_no_plan_amount._inverse_amount_rate()
        self.assertEqual(target_commission_no_plan_amount.amount, 0.0)

    def test_compute_amount(self):
        """
        Test that `_compute_amount` correctly calculates the commission amount
        from `plan_id.commission_amount` and `amount_rate`.
        """
        target_commission = self.env['commission.plan.target.commission'].create({
            'plan_id': self.plan.id,
            'amount_rate': 0.2,
            'company_id': self.company.id,
        })
        target_commission._compute_amount()
        self.assertEqual(target_commission.amount, 200.0)
        target_commission_no_rate = self.env['commission.plan.target.commission'].create({
            'plan_id': self.plan.id,
            'amount_rate': 0.0,
            'company_id': self.company.id,
        })
        target_commission_no_rate._compute_amount()
        self.assertEqual(target_commission_no_rate.amount, 0.0)
    def test_inverse_amount(self):
        """
        """
        target_commission = self.env['commission.plan.target.commission'].create({
            'plan_id': self.plan.id,
            'amount': 200.0,
            'company_id': self.company.id,
        })
        target_commission._inverse_amount()
        self.assertAlmostEqual(target_commission.amount_rate, 0.2, 2)
        target_commission_no_value = self.env['commission.plan.target.commission'].create({
            'plan_id': self.plan.id,
            'amount': 0.0,
            'company_id': self.company.id,
        })
        target_commission_no_value._inverse_amount()
        self.assertEqual(target_commission_no_value.amount_rate, 0.0)
