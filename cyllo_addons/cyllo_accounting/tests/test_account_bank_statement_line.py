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


class TestAccountBankStatementLine(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(TestAccountBankStatementLine, cls).setUpClass()
        cls.company = cls.env.user.company_id
        cls.partner = cls.env['res.partner'].create({
            'name': 'Test Bank Partner',
        })
        cls.bank_journal = cls.env['account.journal'].search([
            ('type', '=', 'bank'),
            ('company_id', '=', cls.company.id),
        ], limit=1)
        cls.StatementLine = cls.env['account.bank.statement.line']

    def test_model_loaded(self):
        """Test that the model is correctly loaded."""
        self.assertTrue('account.bank.statement.line' in self.env)

    def test_statement_line_creation(self):
        """Test creating a bank statement line."""
        if not self.bank_journal:
            return
        st_line = self.StatementLine.create({
            'journal_id': self.bank_journal.id,
            'payment_ref': 'Test Payment Ref',
            'amount': 500.0,
            'date': fields.Date.today(),
            'partner_id': self.partner.id,
        })
        self.assertTrue(st_line.id)
        self.assertEqual(st_line.payment_ref, 'Test Payment Ref')
        self.assertEqual(st_line.amount, 500.0)

    def test_compute_account_id(self):
        """Test _compute_account_id populates the account from the move."""
        if not self.bank_journal:
            return
        st_line = self.StatementLine.create({
            'journal_id': self.bank_journal.id,
            'payment_ref': 'Test Compute Account',
            'amount': 100.0,
            'date': fields.Date.today(),
        })
        st_line._compute_account_id()
        # account_id should be computed from move_id.line_ids
        if st_line.move_id and st_line.move_id.line_ids:
            self.assertTrue(st_line.account_id)

    def test_compute_amount_in_base(self):
        """Test _compute_amount_in_base computation."""
        if not self.bank_journal:
            return
        st_line = self.StatementLine.create({
            'journal_id': self.bank_journal.id,
            'payment_ref': 'Test Base Amount',
            'amount': 200.0,
            'date': fields.Date.today(),
        })
        st_line._compute_amount_in_base()
        self.assertTrue(st_line.amount_in_base != 0 or st_line.amount == 0)

    def test_compute_currency_rate(self):
        """Test _compute_currency_rate computation."""
        if not self.bank_journal:
            return
        st_line = self.StatementLine.create({
            'journal_id': self.bank_journal.id,
            'payment_ref': 'Test Currency Rate',
            'amount': 100.0,
            'date': fields.Date.today(),
        })
        st_line._compute_currency_rate()
        self.assertTrue(st_line.currency_rate > 0)

    def test_toggle_to_check(self):
        """Test toggle_to_check method toggles the to_check flag."""
        if not self.bank_journal:
            return
        st_line = self.StatementLine.create({
            'journal_id': self.bank_journal.id,
            'payment_ref': 'Toggle Test',
            'amount': 50.0,
            'date': fields.Date.today(),
        })
        # Initially to_check should be False
        self.assertFalse(st_line.to_check)
        # Toggle on
        self.StatementLine.toggle_to_check(st_line.id)
        st_line.invalidate_recordset()
        self.assertTrue(st_line.to_check)
        # Toggle off
        self.StatementLine.toggle_to_check(st_line.id)
        st_line.invalidate_recordset()
        self.assertFalse(st_line.to_check)

    def test_update_statement_line_fields_partner(self):
        """Test update_statement_line_fields with partner_id data."""
        if not self.bank_journal:
            return
        st_line = self.StatementLine.create({
            'journal_id': self.bank_journal.id,
            'payment_ref': 'Update Fields Test',
            'amount': 75.0,
            'date': fields.Date.today(),
        })
        st_line.update_statement_line_fields({
            'partner_id': [self.partner.id, self.partner.name]
        })
        self.assertEqual(st_line.partner_id.id, self.partner.id)

    def test_update_statement_line_fields_other(self):
        """Test update_statement_line_fields with non-partner data."""
        if not self.bank_journal:
            return
        st_line = self.StatementLine.create({
            'journal_id': self.bank_journal.id,
            'payment_ref': 'Update Other Test',
            'amount': 75.0,
            'date': fields.Date.today(),
        })
        st_line.update_statement_line_fields({
            'payment_ref': 'Updated Ref'
        })
        self.assertEqual(st_line.payment_ref, 'Updated Ref')

    def test_get_move_line_read_fields_property(self):
        """Test _get_move_line_read_fields returns expected field list."""
        if not self.bank_journal:
            return
        st_line = self.StatementLine.create({
            'journal_id': self.bank_journal.id,
            'payment_ref': 'Fields Test',
            'amount': 10.0,
            'date': fields.Date.today(),
        })
        fields_list = st_line._get_move_line_read_fields
        self.assertIn('account_id', fields_list)
        self.assertIn('partner_id', fields_list)
        self.assertIn('amount_residual', fields_list)

    def test_compute_foreign_currency_rate_no_currency(self):
        """Test _compute_foreign_currency_rate when no foreign currency set."""
        if not self.bank_journal:
            return
        st_line = self.StatementLine.create({
            'journal_id': self.bank_journal.id,
            'payment_ref': 'No FC Test',
            'amount': 10.0,
            'date': fields.Date.today(),
        })
        st_line._compute_foreign_currency_rate()
        self.assertEqual(st_line.foreign_currency_rate, 0)

    def test_cron_reconcile_method(self):
        """Test cron_reconcile_bank_bank_statement_line runs without error."""
        self.StatementLine.cron_reconcile_bank_bank_statement_line()
        self.assertTrue(True)
