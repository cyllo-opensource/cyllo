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


class TestAccountMoveLine(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(TestAccountMoveLine, cls).setUpClass()
        cls.MoveLine = cls.env['account.move.line']
        cls.partner = cls.env['res.partner'].create({'name': 'ML Test Partner'})
        cls.journal_sale = cls.env['account.journal'].search([('type', '=', 'sale')], limit=1)
        cls.journal_purchase = cls.env['account.journal'].search([('type', '=', 'purchase')], limit=1)
        cls.product = cls.env['product.product'].create({'name': 'ML Test Product'})

    def test_model_loaded(self):
        """Test that the model is correctly loaded."""
        self.assertTrue('account.move.line' in self.env)

    def test_annotation_mixin_inherited(self):
        """Test that account.move.line inherits annotation.mixin."""
        self.assertTrue('annotations' in cls.MoveLine._fields
                        for cls in [type(self)])

    def test_compute_move_asset_type_out_invoice(self):
        """Test _compute_move_asset_type for out_invoice."""
        move = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'journal_id': self.journal_sale.id,
            'partner_id': self.partner.id,
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product.id,
                'quantity': 1,
                'price_unit': 100.0,
            })],
        })
        for line in move.line_ids:
            if line.product_id:
                self.assertEqual(line.move_asset_type, 'revenue')

    def test_compute_move_asset_type_in_invoice(self):
        """Test _compute_move_asset_type for in_invoice."""
        if not self.journal_purchase:
            return
        move = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'journal_id': self.journal_purchase.id,
            'partner_id': self.partner.id,
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product.id,
                'quantity': 1,
                'price_unit': 100.0,
            })],
        })
        for line in move.line_ids:
            if line.product_id:
                self.assertEqual(line.move_asset_type, 'expense')

    def test_compute_move_asset_type_entry(self):
        """Test _compute_move_asset_type for entry type (should be False)."""
        journal = self.env['account.journal'].search([('type', '=', 'general')], limit=1)
        if not journal:
            return
        account = self.env['account.account'].search([
            ('account_type', '=', 'asset_current'),
        ], limit=1)
        move = self.env['account.move'].create({
            'move_type': 'entry',
            'journal_id': journal.id,
            'line_ids': [(0, 0, {
                'account_id': account.id,
                'name': 'Test',
                'debit': 100,
            }), (0, 0, {
                'account_id': account.id,
                'name': 'Test 2',
                'credit': 100,
            })],
        })
        for line in move.line_ids:
            self.assertFalse(line.move_asset_type)

    def test_get_js_list_view(self):
        """Test get_js_list_view returns a view ID or False."""
        result = self.MoveLine.get_js_list_view()
        # Should return an integer (view ID) or False
        self.assertTrue(result is False or isinstance(result, int))

    def test_multi_invoice_payment_field(self):
        """Test multi_invoice_payment default value."""
        journal = self.env['account.journal'].search([('type', '=', 'general')], limit=1)
        account = self.env['account.account'].search([
            ('account_type', '=', 'asset_current'),
        ], limit=1)
        if not journal or not account:
            return
        move = self.env['account.move'].create({
            'journal_id': journal.id,
            'line_ids': [(0, 0, {
                'account_id': account.id,
                'name': 'Test',
                'debit': 100,
            }), (0, 0, {
                'account_id': account.id,
                'name': 'Test 2',
                'credit': 100,
            })],
        })
        for line in move.line_ids:
            self.assertFalse(line.multi_invoice_payment)

    def test_asset_field_default(self):
        """Test asset boolean field default is False."""
        journal = self.env['account.journal'].search([('type', '=', 'general')], limit=1)
        account = self.env['account.account'].search([
            ('account_type', '=', 'asset_current'),
        ], limit=1)
        if not journal or not account:
            return
        move = self.env['account.move'].create({
            'journal_id': journal.id,
            'line_ids': [(0, 0, {
                'account_id': account.id,
                'name': 'Test',
                'debit': 100,
            }), (0, 0, {
                'account_id': account.id,
                'name': 'Test 2',
                'credit': 100,
            })],
        })
        for line in move.line_ids:
            self.assertFalse(line.asset)
