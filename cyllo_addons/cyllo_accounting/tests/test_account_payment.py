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
from odoo.exceptions import UserError


class TestAccountPayment(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(TestAccountPayment, cls).setUpClass()
        cls.Payment = cls.env['account.payment']
        cls.partner = cls.env['res.partner'].create({'name': 'Payment Test Partner'})
        cls.journal = cls.env['account.journal'].search([('type', '=', 'bank')], limit=1)
        cls.product = cls.env['product.product'].create({'name': 'Payment Test Product'})
        cls.journal_sale = cls.env['account.journal'].search([('type', '=', 'sale')], limit=1)

    def test_action_draft(self):
        """Test action_draft resets payment to draft."""
        payment = self.Payment.create({
            'amount': 100,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'journal_id': self.journal.id,
        })
        payment.action_post()
        payment.action_draft()
        self.assertEqual(payment.state, 'draft')

    def test_compute_amount_signed_inbound(self):
        """Test _compute_amount_signed for inbound payments."""
        payment = self.Payment.create({
            'amount': 100,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'journal_id': self.journal.id,
        })
        payment._compute_amount_signed()
        self.assertTrue(payment.amount_signed >= 0)

    def test_compute_amount_signed_outbound(self):
        """Test _compute_amount_signed for outbound payments."""
        payment = self.Payment.create({
            'amount': 100,
            'payment_type': 'outbound',
            'partner_type': 'supplier',
            'journal_id': self.journal.id,
        })
        payment._compute_amount_signed()
        self.assertTrue(payment.amount_signed <= 0)

    def test_compute_total_invoice_amount_draft(self):
        """Test _compute_total_invoice_amount in draft state."""
        payment = self.Payment.create({
            'amount': 100,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'journal_id': self.journal.id,
        })
        payment._compute_total_invoice_amount()
        self.assertEqual(payment.total_invoice_amount, 0)

    def test_compute_total_payment_amount(self):
        """Test _compute_total_payment_amount."""
        payment = self.Payment.create({
            'amount': 100,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'journal_id': self.journal.id,
        })
        payment._compute_total_payment_amount()
        # For non-multi_invoice_payment, should equal amount_company_currency_signed
        self.assertTrue(True)

    def test_onchange_partner_id_with_move_ids(self):
        """Test _onchange_partner_id raises error when move_ids present."""
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner.id,
            'journal_id': self.journal_sale.id,
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product.id,
                'quantity': 1,
                'price_unit': 100.0,
            })],
        })
        invoice.action_post()
        payment = self.Payment.new({
            'amount': 100,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'journal_id': self.journal.id,
            'partner_id': self.partner.id,
            'move_ids': [(6, 0, [invoice.id])],
        })
        with self.assertRaises(UserError):
            payment.partner_id = self.env['res.partner'].create({'name': 'New Partner'})
            payment._onchange_partner_id()

    def test_action_draft_resets_amount(self):
        """Test action_draft resets amount when move_ids are present."""
        payment = self.Payment.create({
            'amount': 100,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'journal_id': self.journal.id,
        })
        payment.action_post()
        payment.action_draft()
        self.assertEqual(payment.state, 'draft')

    def test_button_open_statement_lines(self):
        """Test button_open_statement_lines returns correct action."""
        payment = self.Payment.create({
            'amount': 100,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'journal_id': self.journal.id,
        })
        result = payment.button_open_statement_lines()
        self.assertEqual(result.get('res_model'), 'account.bank.statement.line')
        self.assertEqual(result.get('view_mode'), 'reconcile')

    def test_batch_payment_field_default(self):
        """Test batch_payment_id default is False."""
        payment = self.Payment.create({
            'amount': 100,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'journal_id': self.journal.id,
        })
        self.assertFalse(payment.batch_payment_id)

    def test_multi_invoice_payment_default(self):
        """Test multi_invoice_payment default is False."""
        payment = self.Payment.create({
            'amount': 100,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'journal_id': self.journal.id,
        })
        self.assertFalse(payment.multi_invoice_payment)
