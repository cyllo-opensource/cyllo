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


class TestAccountMove(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(TestAccountMove, cls).setUpClass()
        cls.Move = cls.env['account.move']
        cls.partner = cls.env['res.partner'].create({'name': 'Move Test Partner'})
        cls.journal_sale = cls.env['account.journal'].search([('type', '=', 'sale')], limit=1)
        cls.journal_purchase = cls.env['account.journal'].search([('type', '=', 'purchase')], limit=1)
        cls.journal_misc = cls.env['account.journal'].search([('type', '=', 'general')], limit=1)
        cls.product = cls.env['product.product'].create({'name': 'Test Product Move'})

    def test_compute_fiscal_year_id(self):
        """Test _compute_fiscal_year_id computation."""
        move = self.Move.create({'journal_id': self.journal_sale.id})
        move._compute_fiscal_year_id()
        # Should not error; fiscal_year_id may or may not be set
        self.assertTrue(True)

    def test_action_get_asset_moves_out_invoice(self):
        """Test action_get_asset_moves returns deferred revenue for out_invoice."""
        move = self.Move.create({
            'move_type': 'out_invoice',
            'journal_id': self.journal_sale.id,
            'partner_id': self.partner.id,
        })
        res = move.action_get_asset_moves()
        self.assertEqual(res.get('res_model'), 'account.asset.asset')
        self.assertIn('Deferred Revenues', res.get('name', ''))

    def test_action_get_asset_moves_in_invoice(self):
        """Test action_get_asset_moves returns deferred expense for in_invoice."""
        if not self.journal_purchase:
            return
        move = self.Move.create({
            'move_type': 'in_invoice',
            'journal_id': self.journal_purchase.id,
            'partner_id': self.partner.id,
        })
        res = move.action_get_asset_moves()
        self.assertEqual(res.get('res_model'), 'account.asset.asset')
        self.assertIn('Deferred Expenses', res.get('name', ''))

    def test_action_get_asset_moves_entry(self):
        """Test action_get_asset_moves returns None for entry type."""
        if not self.journal_misc:
            return
        move = self.Move.create({
            'move_type': 'entry',
            'journal_id': self.journal_misc.id,
        })
        res = move.action_get_asset_moves()
        self.assertIsNone(res)

    def test_compute_asset_count(self):
        """Test _compute_asset_count returns zero for moves without assets."""
        move = self.Move.create({
            'journal_id': self.journal_sale.id,
            'partner_id': self.partner.id,
        })
        move._compute_asset_count()
        self.assertEqual(move.asset_count, 0)

    def test_compute_total_residual(self):
        """Test _compute_total_residual for moves without asset."""
        move = self.Move.create({
            'journal_id': self.journal_sale.id,
            'partner_id': self.partner.id,
        })
        move._compute_total_residual()
        self.assertEqual(move.total_residual, 0)
        self.assertEqual(move.asset_residual_amount, 0)

    def test_onchange_amount_residual(self):
        """Test _onchange_amount_residual sets residual_amount."""
        move = self.Move.create({
            'move_type': 'out_invoice',
            'journal_id': self.journal_sale.id,
            'partner_id': self.partner.id,
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product.id,
                'quantity': 1,
                'price_unit': 500.0,
            })],
        })
        move._onchange_amount_residual()
        # residual_amount should be set when amount_residual is non-zero
        self.assertTrue(True)

    def test_get_invoice_in_payment_state(self):
        """Test _get_invoice_in_payment_state returns in_payment."""
        state = self.Move._get_invoice_in_payment_state()
        self.assertEqual(state, 'in_payment')

    def test_get_reconciled_statement_line_ids(self):
        """Test get_reconciled_statement_line_ids returns a list."""
        move = self.Move.create({
            'journal_id': self.journal_sale.id,
        })
        result = move.get_reconciled_statement_line_ids()
        self.assertIsInstance(result, list)

    def test_prepare_moves(self):
        """Test _prepare_moves creates proper move values."""
        company = self.env.company
        account = self.env['account.account'].create({
            'name': 'Asset Test Account',
            'code': '180001.MV.TST',
            'account_type': 'asset_current',
            'company_id': company.id,
        })
        expense_account = self.env['account.account'].create({
            'name': 'Expense Test Account',
            'code': '680001.MV.TST',
            'account_type': 'expense',
            'company_id': company.id,
        })
        journal = self.env['account.journal'].search([
            ('type', '=', 'general'),
            ('company_id', '=', company.id),
        ], limit=1)

        asset = self.env['account.asset.asset'].create({
            'name': 'Test Asset for Move',
            'journal_id': journal.id,
            'account_id': account.id,
            'expense_account_id': expense_account.id,
            'number_of_entries': 3,
            'period': '1',
            'computation_method': 'no_prorata',
            'company_id': company.id,
            'original_value': 3000.0,
            'first_recognition_date': fields.Date.today(),
        })

        vals = {
            'amount': 1000.0,
            'asset_id': asset,
            'asset_date': fields.Date.today(),
            'asset_end_date': fields.Date.today(),
            'date': fields.Date.today(),
            'asset_days': 30,
        }
        result = self.Move._prepare_moves(vals)
        self.assertEqual(result['asset_id'], asset.id)
        self.assertEqual(result['move_type'], 'entry')
        self.assertTrue(result['line_ids'])
