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
from odoo.addons.cyllo_asset_management.tests.common import TestCommon


class TestAccountMove(TestCommon):
    """Test for account move"""

    def test_compute_asset_asset_count(self):
        """Test for _compute_asset_asset_count function"""
        self.account_move._compute_asset_asset_count()
        self.assertEqual(self.account_move.asset_asset_count, len(self.account_move.asset_asset_ids))

    def test_create_account_asset_moves(self):
        """Test of create_account_asset_moves function."""
        invoice_line = self.account_move.invoice_line_ids[0]
        self.assertTrue(self.account_move.is_invoice())
        self.assertEqual(invoice_line.account_id.account_type, 'asset_fixed')
        self.assertTrue(invoice_line.account_id.multiple_asset)
        self.assertNotEqual(invoice_line.account_id.asset_creation, 'no')
        self.account_move.create_account_asset_moves()
        created_assets = self.account_move.asset_asset_ids
        self.assertEqual(len(created_assets), 2)


    def test_post(self):
        """Test of function _post"""
        move = self.account_move
        move.asset_asset_id.depreciation_line_ids = move.depreciation_line_id.ids
        self.account_move._post()
        self.assertEqual(move.state, 'posted')

    def test_button_draft(self):
        """Test of button_draft function"""
        self.asset_asset = self.env['asset.asset'].create({
            'name': 'XYZ',
            'asset_item_id': self.item_id.id,
            'original_value': 5,
            'salvage_value': 5,
            'fixed_asset_account_id': self.account_1.id,
            'asset_depreciation_account_id': self.account_1.id,
            'asset_expense_account_id': self.account_3.id,
            'asset_loss_account_id': self.account_3.id,
            'asset_journal_id': self.asset_journal_id.id,
            'is_depreciate': True,
            'status': 'draft',
            'depreciation_method': 'straight_line',
            'computation_method': 'no_prorata',
        })
        self.account_move.asset_asset_ids = self.asset_asset.ids
        self.account_move.state = 'posted'
        with self.assertRaises(UserError):
            self.account_move.button_draft()
        self.account_move.asset_asset_ids.is_depreciate = False
        self.account_move.button_draft()
        self.assertEqual(self.account_move.asset_asset_ids.id, False)
