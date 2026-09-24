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

class TestAccountAssetType(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(TestAccountAssetType, cls).setUpClass()
        cls.company = cls.env.user.company_id
        
        cls.account = cls.env['account.account'].create({
            'name': 'Type Account',
            'code': '101001',
            'account_type': 'asset_current',
            'company_id': cls.company.id,
        })
        
        cls.expense_account = cls.env['account.account'].create({
            'name': 'Type Expense Account',
            'code': '601001',
            'account_type': 'expense',
            'company_id': cls.company.id,
        })
        
        cls.journal = cls.env['account.journal'].create({
            'name': 'Type Journal',
            'code': 'TYP',
            'type': 'general',
            'company_id': cls.company.id,
        })

        cls.AssetType = cls.env['account.asset.type']

    def test_compute_type(self):
        """Test _compute_type logic with context."""
        asset_type = self.AssetType.with_context(type='expense').create({
            'name': 'Expense Type',
            'journal_id': self.journal.id,
            'account_id': self.account.id,
            'expense_account_id': self.expense_account.id,
            'number_of_entries': 12,
            'period': '1',
            'computation_method': 'no_prorata',
        })
        self.assertEqual(asset_type.type, 'expense')

    def test_copy_data(self):
        """Test copy_data method."""
        asset_type = self.AssetType.create({
            'name': 'Original Type',
            'journal_id': self.journal.id,
            'account_id': self.account.id,
            'expense_account_id': self.expense_account.id,
            'number_of_entries': 12,
            'period': '1',
            'computation_method': 'no_prorata',
        })
        copied_type = asset_type.copy()
        self.assertEqual(copied_type.name, 'Original Type (copy)')
