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
        """Test of create_account_asset_moves function"""
        self.account_move.create_account_asset_moves()
        latest_asset = self.env['asset.asset'].search([], order='id desc', limit=1)
        self.assertEqual(self.env.ref("product.product_product_4").list_price, latest_asset.original_value)
        self.assertIn(latest_asset, self.account_move.asset_asset_ids)
        self.account_2.multiple_asset = False
        latest_asset.original_value = 0
        self.account_move.create_account_asset_moves()
        self.assertEqual(self.account_move, latest_asset.invoice_id)
        self.assertIn(latest_asset, self.account_move.asset_asset_ids)
        self.account_2.asset_creation = 'validate'
        self.account_move.create_account_asset_moves()


    def test_post(self):
        """Test of function _post"""
        move = self.account_move
        move.asset_asset_id.depreciation_line_ids = move.depreciation_line_id.ids
        self.account_move._post()
        depreciation_line = move.asset_asset_id.depreciation_line_ids.filtered(
                lambda d: d.id == move.depreciation_line_id.id)
        self.assertEqual(depreciation_line.journal_reference, move.name)

    def test_button_draft(self):
        """Test of button_draft function"""
        self.asset_asset = self.env['asset.asset'].create({
            'name': 'XYZ',
            'asset_item_id': self.item_id.id,
            'asset_type_id': self.asset_type.id,
            'original_value': 5,
            'salvage_value': 5,
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
