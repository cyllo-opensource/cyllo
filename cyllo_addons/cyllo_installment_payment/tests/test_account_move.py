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
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta


class TestAccountMove(TransactionCase):
    """
    Test cases for account.move related to installment payments.

    Covers:
    - Advance payment computation
    - Installment generation and computation
    - Action button behaviors (post, cancel, draft, compute installments)
    """
    @classmethod
    def setUpClass(cls):
        """
         Setup common records for all tests:
        - Partner
        - Product
        - Invoice with installment payment enabled
        - Journal and Payment
        - Sample Installments
        """
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({'name': 'Partner'})
        cls.product = cls.env['product.product'].create({
            'name': 'Test Product',
            'list_price': 100.0,
        })
        cls.invoice = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': cls.partner.id,
            'invoice_date_due': date.today() + relativedelta(months=1),
            'date': date.today(),
            'installment_payment': True,
            'amount_residual': 5000.0,
            'advance_payment_amount': 1000.0,
            'duration': 4,
            'invoice_line_ids': [(0, 0, {
                'product_id': cls.product.id,
                'quantity': 5,
                'price_unit': 1000.0,
            })],
        })
        cls.journal = cls.env['account.journal'].search([('type', '=', 'bank')],
                                                        limit=1)
        cls.payment = cls.env['account.payment'].create({
            'partner_id': cls.partner.id,
            'amount': 100.0,
            'payment_type': 'inbound',
            'payment_method_id': cls.env.ref(
                'account.account_payment_method_manual_in').id,
            'journal_id': cls.journal.id,
        })
        cls.installment1 = cls.env['account.installment'].create({
            'name': 'Installment 1',
            'sequence': 1,
            'state': 'draft',
            'pay_amount': 1000.0,
            'payment_date': date.today() + relativedelta(months=1),
            'move_id': cls.invoice.id,
        })
        cls.installment2 = cls.env['account.installment'].create({
            'name': 'Installment 2',
            'sequence': 2,
            'state': 'draft',
            'pay_amount': 2000.0,
            'payment_date': date.today() + relativedelta(months=2),
            'move_id': cls.invoice.id,
        })
        cls.installment3 = cls.env['account.installment'].create({
            'name': 'Installment 3',
            'sequence': 3,
            'state': 'draft',
            'pay_amount': 3000.0,
            'payment_date': date.today() + relativedelta(months=3),
            'move_id': cls.invoice.id,
        })
    def test_compute_advance_payment_ids(self):
        """
        Test that advance payments are correctly computed for invoices and bills.
        Verifies:
        - No advance payments initially
        - Adding a payment links it as advance
        - Correct total advance amount calculation
        """
        self.invoice._compute_advance_payment_ids()
        self.assertFalse(self.invoice.advance_payment_ids)
        self.assertEqual(self.invoice.total_advance_paid_amount, 0.0)
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
        })
        sale_line = self.env['sale.order.line'].create({
            'order_id': sale_order.id,
            'product_id': self.product.id,
            'name': 'Test Product',
            'product_uom_qty': 1,
            'price_unit': 100.0,
        })
        self.invoice.write({
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product.id,
                'quantity': 1,
                'price_unit': 100.0,
                'sale_line_ids': [(4, sale_line.id)],
            })]
        })
        self.payment.write({
            'sale_id': sale_order.id,
            'reconciled_invoice_ids': [(4, self.invoice.id)],
        })
        self.invoice._compute_advance_payment_ids()
        self.assertIn(self.payment, self.invoice.advance_payment_ids)
        self.assertEqual(self.invoice.total_advance_paid_amount, 100.0)
        bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner.id,
        })
        purchase_order = self.env['purchase.order'].create({
            'partner_id': self.partner.id,
        })
        purchase_line = self.env['purchase.order.line'].create({
            'order_id': purchase_order.id,
            'product_id': self.product.id,
            'name': 'Test Product',
            'product_qty': 1,
            'price_unit': 200.0,
        })
        bill.write({
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product.id,
                'quantity': 1,
                'price_unit': 200.0,
                'purchase_line_id': purchase_line.id,
            })]
        })
        payment = self.env['account.payment'].create({
            'partner_id': self.partner.id,
            'amount': 200.0,
            'payment_type': 'outbound',
            'payment_method_id': self.env.ref(
                'account.account_payment_method_manual_out').id,
            'journal_id': self.journal.id,
            'purchase_id': purchase_order.id,
            'reconciled_bill_ids': [(4, bill.id)],
        })
        bill._compute_advance_payment_ids()
        self.assertIn(payment, bill.advance_payment_ids)
        self.assertEqual(bill.total_advance_paid_amount, 200.0)
    def test_compute_installment_paid(self):
        """
        Test the calculation of paid and pending installment amounts.
        Verifies:
        - Correct installment_paid and installment_to_pay
        - Next installment date computation
        """
        self.installment1.write({'state': 'draft'})
        self.installment2.write({'state': 'draft'})
        self.installment3.write({'state': 'draft'})
        self.invoice._compute_installment_paid()
        self.assertEqual(self.invoice.installment_paid, 0.0)
        self.assertEqual(self.invoice.installment_to_pay, 6000.0)
        self.assertEqual(self.invoice.next_installment_date,
                         date.today() + relativedelta(months=1))
        self.installment1.write({'state': 'paid'})
        self.installment2.write({'state': 'paid'})
        self.installment3.write({'state': 'draft'})
        self.invoice._compute_installment_paid()
        self.assertEqual(self.invoice.installment_paid, 3000.0)
        self.assertEqual(self.invoice.installment_to_pay, 3000.0)
        self.assertEqual(self.invoice.next_installment_date,
                         date.today() + relativedelta(months=3))
        self.installment3.write({'state': 'paid'})
        self.invoice._compute_installment_paid()
        self.assertEqual(self.invoice.installment_paid, 6000.0)
        self.assertEqual(self.invoice.installment_to_pay, 0.0)
        self.assertFalse(self.invoice.next_installment_date)
    def test_compute_installment_dates(self):
        """
        Test computation of installment due dates based on invoice due date and
        duration.
        """
        self.invoice.write({
            'invoice_date_due': date.today(),
            'duration': 3,
        })
        installment_dates = self.invoice._compute_installment_dates()
        expected_dates = [
            date.today() + relativedelta(months=1),
            date.today() + relativedelta(months=2),
            date.today() + relativedelta(months=3),
        ]
        self.assertEqual(installment_dates, expected_dates)
        today = date.today()

        self.invoice.write({
            'invoice_date_due': False,
            'duration': 2,
        })
        installment_dates = self.invoice._compute_installment_dates()
        expected_dates = [
            today + relativedelta(months=1),
            today + relativedelta(months=2),
        ]
        self.assertEqual(installment_dates, expected_dates)
    def test_generate_installments(self):
        """
        Test that installments are generated correctly from invoice amounts.
        Verifies:
        - Correct number of installments including advance
        - Each installment amount
        - Payment dates
        - Raises UserError when advance > residual or duration = 0
        """
        self.invoice.write({
            'amount_residual': 6000.0,
            'advance_payment_amount': 1000.0,
            'duration': 4,
        })
        self.invoice._generate_installments()
        installments = self.invoice.installment_ids.sorted("sequence")
        self.assertEqual(len(installments), 5)
        self.assertTrue(installments[0].is_advance)
        self.assertEqual(installments[0].pay_amount, 1000.0)
        for inst in installments[1:]:
            self.assertAlmostEqual(inst.pay_amount, 1250.0)
        total = sum(inst.pay_amount for inst in installments)
        self.assertAlmostEqual(total, 6000.0)
        self.invoice.write({
            'amount_residual': 9000.0,
            'advance_payment_amount': 0.0,
            'duration': 3,
        })
        self.invoice._generate_installments()
        installments = self.invoice.installment_ids.sorted("sequence")
        self.assertEqual(len(installments), 3)
        for inst in installments:
            self.assertAlmostEqual(inst.pay_amount, 3000.0)
        expected_dates = [date.today() + relativedelta(months=2),
                          date.today() + relativedelta(months=3),
                          date.today() + relativedelta(months=4)]
        self.assertEqual([inst.payment_date for inst in installments],
                         expected_dates)
        self.invoice.write({
            'amount_residual': 10000.0,
            'advance_payment_amount': 0.0,
            'duration': 3,
        })
        self.invoice._generate_installments()
        installments = self.invoice.installment_ids.sorted("sequence")
        self.assertEqual(len(installments), 3)
        self.assertAlmostEqual(installments[0].pay_amount,
                               3333.3333333333335)
        self.assertAlmostEqual(installments[1].pay_amount,
                               3333.3333333333335)
        total = sum(inst.pay_amount for inst in installments)
        self.assertAlmostEqual(round(total, 2), 10000.01)
        self.invoice.write({
            'amount_residual': 5000.0,
            'advance_payment_amount': 6000.0,
            'duration': 2,
        })
        with self.assertRaises(UserError):
            self.invoice._generate_installments()
        self.invoice.write({
            'amount_residual': 5000.0,
            'advance_payment_amount': 1000.0,
            'duration': 0,
        })
        with self.assertRaises(UserError):
            self.invoice._generate_installments()

    def test_action_post(self):
        """
        Test action_post method for invoices.
        Ensures that:
        - Installments are generated upon posting
        - Advance and regular installment amounts are correct
        - All installments are marked ready_to_pay
        """
        self.invoice.action_post()
        installments = self.invoice.installment_ids.sorted("sequence")
        self.assertEqual(len(installments), 5)
        self.assertTrue(installments[0].is_advance)
        self.assertEqual(installments[0].pay_amount, 1000.0)
        remaining_amount = self.invoice.amount_residual - installments[
            0].pay_amount
        duration = self.invoice.duration
        base_amount = round(remaining_amount / duration, 2)
        for i, inst in enumerate(installments[1:], start=1):
            if i < len(installments) - 1:
                self.assertAlmostEqual(inst.pay_amount, base_amount)
            else:
                expected_last = remaining_amount - base_amount * (duration - 1)
                self.assertAlmostEqual(inst.pay_amount, expected_last)
        total_amount = sum(inst.pay_amount for inst in installments)
        self.assertAlmostEqual(total_amount, self.invoice.amount_residual)
        self.assertTrue(all(installments.mapped('ready_to_pay')))
    def test_button_cancel(self):
        """
        Test button_cancel method.
        Ensures that all linked installments are canceled when the invoice is
         canceled.
        """
        self.invoice._generate_installments()
        installments = self.invoice.installment_ids.sorted("sequence")
        self.assertTrue(installments)
        self.assertFalse(any(inst.state == 'cancel' for inst in installments))
        self.invoice.button_cancel()
        self.assertEqual(self.invoice.state, 'cancel')
        for inst in installments:
            self.assertEqual(inst.state, 'cancel')
    def test_button_draft(self):
        """
        Test button_draft method.
        Ensures that all linked installments are reset to not ready_to_pay when
        invoice is set to draft.
        """
        self.invoice._generate_installments()
        for inst in self.invoice.installment_ids:
            inst.ready_to_pay = True
        self.invoice.action_post()
        self.assertTrue(
            all(self.invoice.installment_ids.mapped('ready_to_pay')))
        self.invoice.button_draft()
        self.assertEqual(self.invoice.state, 'draft')
        for inst in self.invoice.installment_ids:
            self.assertFalse(inst.ready_to_pay)
    def test_action_button_compute_installments(self):
        """
        Test action_button_compute_installments method.
        Ensures that installments are generated only if installment_payment is True.
        Verifies:
        - Correct number of installments
        - First installment is advance
        - Installment amounts are correct
        - No new installments are generated if installment_payment is False
        """
        self.invoice.write({
            'installment_payment': True,
            'amount_residual': 6000.0,
            'advance_payment_amount': 1000.0,
            'duration': 4,
        })
        self.invoice.action_button_compute_installments()
        installments = self.invoice.installment_ids.sorted("sequence")
        self.assertEqual(len(installments), 5)
        self.assertTrue(installments[0].is_advance)
        self.assertEqual(installments[0].pay_amount, 1000.0)
        expected_amount = (6000.0 - 1000.0) / 4
        for inst in installments[1:]:
            self.assertAlmostEqual(inst.pay_amount, expected_amount)
        self.invoice.write({'installment_payment': False})
        self.invoice.action_button_compute_installments()
        self.assertEqual(len(self.invoice.installment_ids), 5)
