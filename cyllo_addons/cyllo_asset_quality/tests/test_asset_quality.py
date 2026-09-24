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
from unittest.mock import patch
from odoo.tests.common import TransactionCase
from odoo import fields


class TestAssetQuality(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.AssetItem = cls.env['asset.item']
        cls.AssetAsset = cls.env['asset.asset']
        cls.Account = cls.env['account.account']
        cls.Journal = cls.env['account.journal']
        cls.company = cls.env.company
        cls.fixed_asset_account = cls.Account.create({
            'name': 'Fixed Asset Account',
            'code': 'FA001',
            'account_type': 'asset_fixed',
            'company_id': cls.company.id,
        })
        cls.asset_depreciation_account = cls.Account.create({
            'name': 'Depreciation Account',
            'code': 'DEP001',
            'account_type': 'asset_current',
            'company_id': cls.company.id,
        })
        cls.asset_expense_account = cls.Account.create({
            'name': 'Expense Account',
            'code': 'EXP001',
            'account_type': 'expense',
            'company_id': cls.company.id,
        })
        cls.asset_loss_account = cls.Account.create({
            'name': 'Loss Account',
            'code': 'LOS001',
            'account_type': 'expense',
            'company_id': cls.company.id,
        })
        cls.asset_journal = cls.Journal.create({
            'name': 'Asset Journal',
            'code': 'AST',
            'type': 'general',
            'company_id': cls.company.id,
        })
        with patch.object(
                type(cls.env['ir.module.module']),
                'button_immediate_install',
                return_value=True
        ):
            cls.asset_item = cls.AssetItem.create({
                'name': 'Test Asset Item',
                'date': fields.Date.today(),
                'prorata_date': fields.Date.today(),
                'duration_period': 'year',
                'computation_method': 'no_prorata',
                'depreciation_method': 'straight_line',
                'depreciating_factor': 30,
                'method_duration': 1,
                'is_auto_calculate': True,
                'is_quality': True,
                'asset_journal_id':
                    cls.asset_journal.id,
                'fixed_asset_account_id':
                    cls.fixed_asset_account.id,
                'asset_depreciation_account_id':
                    cls.asset_depreciation_account.id,
                'asset_expense_account_id':
                    cls.asset_expense_account.id,
                'asset_loss_account_id':
                    cls.asset_loss_account.id,
            })
        cls.asset = cls.AssetAsset.create({
            'name': 'Test Asset',
            'asset_item_id': cls.asset_item.id,
            'original_value': 5000,
            'salvage_value' : 5000,
            'fixed_asset_account_id': cls.fixed_asset_account.id,
            'asset_depreciation_account_id': cls.asset_depreciation_account.id,
            'asset_expense_account_id': cls.asset_expense_account.id,
            'asset_loss_account_id': cls.asset_loss_account.id,
            'asset_journal_id': cls.asset_journal.id,
        })
    def test_asset_item_created(self):
        self.assertTrue(self.asset_item)
        self.assertEqual(
            self.asset_item.name,
            'Test Asset Item'
        )

    def test_asset_created(self):
        self.assertTrue(self.asset)
        self.assertEqual(
            self.asset.asset_item_id.id,
            self.asset_item.id
        )