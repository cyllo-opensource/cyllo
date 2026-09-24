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
from odoo.addons.cyllo_advance_payment.tests.common import \
    TestCylloAdvancePayment
from odoo.exceptions import UserError


class TestAdvancePayment(TestCylloAdvancePayment):

    def test_default_get_sale_order(self):
        wizard = self.env['advance.payment'].with_context(type='sale',
                                                          active_id=self.sale_order.id).default_get(
            [])
        self.assertEqual(wizard['communication'], self.sale_order.name)
        self.assertEqual(wizard['total_amount'], self.sale_order.amount_total - self.sale_order.total_advance_amount)
        self.assertEqual(wizard['pay_amount'], self.sale_order.amount_total - self.sale_order.total_advance_amount)
        self.assertEqual(wizard['partner_id'], self.sale_order.partner_id.id)
        self.assertEqual(wizard['currency_id'], self.sale_order.currency_id.id)
        self.assertEqual(wizard['company_id'], self.sale_order.company_id.id)
        self.assertTrue(wizard['date'])

    def test_default_get_purchase_order(self):
        wizard = self.env['advance.payment'].with_context(type='purchase',
                                                          active_id=self.purchase1.id).default_get(
            [])
        self.assertEqual(wizard['communication'], self.purchase1.name)
        self.assertEqual(wizard['total_amount'], self.purchase1.amount_total - self.purchase1.total_advance_amount)
        self.assertEqual(wizard['pay_amount'], self.purchase1.amount_total - self.purchase1.total_advance_amount)
        self.assertEqual(wizard['partner_id'], self.purchase1.partner_id.id)
        self.assertEqual(wizard['currency_id'], self.purchase1.currency_id.id)
        self.assertEqual(wizard['company_id'], self.purchase1.company_id.id)
        self.assertTrue(wizard['date'])

    def test_compute_journal_id(self):
        wizard = self.env['advance.payment'].create({})
        wizard._compute_journal_id()
        self.assertTrue(wizard.journal_id)

    def test_compute_total_amount(self):
        wizard = self.env['advance.payment'].with_context(
            type='sale', active_id=self.sale_order.id).create({})
        wizard._compute_total_amount()
        self.assertEqual(wizard.total_amount, self.sale_order.amount_total - self.sale_order.total_advance_amount)

    def test_compute_payment_method_line_id(self):
        wizard = self.env['advance.payment'].create({})
        wizard._compute_payment_method_line_id()
        self.assertTrue(wizard.payment_method_line_id)

    def test_onchange_pay_amount(self):
        expected_amount = self.sale_order.amount_total - self.sale_order.total_advance_amount
        wizard = self.env['advance.payment'].with_context(
            type='sale', active_id=self.sale_order.id).create({
                'total_amount': expected_amount,
                'pay_amount': expected_amount,
            })
        wizard._onchange_pay_amount()
        self.assertEqual(wizard.amount_difference, 0.0)

        with self.assertRaises(UserError):
            wizard.pay_amount = wizard.total_amount + 50.0
            wizard._onchange_pay_amount()

    def test_action_validate_payment(self):
        wizard = self.env['advance.payment'].with_context(
            type='sale', active_id=self.sale_order.id).create({
                'pay_amount': 100.0,
            })
        wizard.action_validate_payment()
        payment = self.env['account.payment'].search([], order='id desc',
                                                     limit=1)
        self.assertEqual(payment.amount, 100.0)
        self.assertEqual(payment.payment_type, 'inbound')