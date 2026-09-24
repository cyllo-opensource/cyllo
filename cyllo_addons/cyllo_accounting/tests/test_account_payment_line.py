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
from odoo import fields


class TestAccountPaymentLine(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(TestAccountPaymentLine, cls).setUpClass()
        cls.PaymentLine = cls.env['account.payment.line']
        cls.partner = cls.env['res.partner'].create({'name': 'PL Test Partner'})
        cls.journal_sale = cls.env['account.journal'].search([('type', '=', 'sale')], limit=1)
        cls.journal_bank = cls.env['account.journal'].search([('type', '=', 'bank')], limit=1)
        cls.product = cls.env['product.product'].create({'name': 'PL Test Product'})

        # Create an invoice
        cls.invoice = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': cls.partner.id,
            'journal_id': cls.journal_sale.id,
            'invoice_line_ids': [(0, 0, {
                'product_id': cls.product.id,
                'quantity': 1,
                'price_unit': 500.0,
            })],
        })
        # Create a payment
        cls.payment = cls.env['account.payment'].create({
            'amount': 500,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'journal_id': cls.journal_bank.id,
        })

    def test_model_loaded(self):
        """Test that the model is correctly loaded."""
        self.assertTrue('account.payment.line' in self.env)

    def test_payment_line_creation(self):
        """Test creating a payment line record."""
        payment_line = self.PaymentLine.create({
            'move_id': self.invoice.id,
            'payment_id': self.payment.id,
        })
        self.assertTrue(payment_line.id)
        self.assertEqual(payment_line.move_id.id, self.invoice.id)
        self.assertEqual(payment_line.payment_id.id, self.payment.id)

    def test_related_partner_id(self):
        """Test partner_id is related from move_id."""
        payment_line = self.PaymentLine.create({
            'move_id': self.invoice.id,
            'payment_id': self.payment.id,
        })
        self.assertEqual(payment_line.partner_id.id, self.partner.id)

    def test_related_total_amount(self):
        """Test total_amount is related from move_id.amount_total."""
        payment_line = self.PaymentLine.create({
            'move_id': self.invoice.id,
            'payment_id': self.payment.id,
        })
        self.assertEqual(payment_line.total_amount, self.invoice.amount_total)

    def test_related_pay_amount(self):
        """Test pay_amount is related from move_id.amount_residual."""
        payment_line = self.PaymentLine.create({
            'move_id': self.invoice.id,
            'payment_id': self.payment.id,
        })
        self.assertEqual(payment_line.pay_amount, self.invoice.amount_residual)

    def test_compute_paid_amount(self):
        """Test _compute_paid_amount computation."""
        payment_line = self.PaymentLine.create({
            'move_id': self.invoice.id,
            'payment_id': self.payment.id,
        })
        payment_line._compute_paid_amount()
        # paid_amount = total - residual (when paid_amount is 0)
        expected = self.invoice.amount_total - self.invoice.amount_residual
        self.assertEqual(payment_line.paid_amount, expected)

    def test_related_currency_id(self):
        """Test currency_id is related from move_id.currency_id."""
        payment_line = self.PaymentLine.create({
            'move_id': self.invoice.id,
            'payment_id': self.payment.id,
        })
        self.assertEqual(payment_line.currency_id.id, self.invoice.currency_id.id)

    def test_rec_name(self):
        """Test _rec_name is move_id."""
        self.assertEqual(self.PaymentLine._rec_name, 'move_id')
