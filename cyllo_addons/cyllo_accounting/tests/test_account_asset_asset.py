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
from odoo.exceptions import UserError
from datetime import date

class TestAccountAssetAsset(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(TestAccountAssetAsset, cls).setUpClass()
        cls.company = cls.env.user.company_id
        
        # Create an account
        cls.account = cls.env['account.account'].create({
            'name': 'Asset Account',
            'code': '101000.TEST.AST',
            'account_type': 'asset_current',
            'company_id': cls.company.id,
        })
        
        # Create expense account
        cls.expense_account = cls.env['account.account'].create({
            'name': 'Expense Account',
            'code': '601000.TEST.EXP',
            'account_type': 'expense',
            'company_id': cls.company.id,
        })
        
        # Create journal
        cls.journal = cls.env['account.journal'].create({
            'name': 'Asset Journal',
            'code': 'AST_T',
            'type': 'general',
            'company_id': cls.company.id,
        })

        cls.Asset = cls.env['account.asset.asset']
        
        cls.asset = cls.Asset.create({
            'name': 'Test Deferred Revenue',
            'asset_type': 'revenue',
            'journal_id': cls.journal.id,
            'account_id': cls.account.id,
            'expense_account_id': cls.expense_account.id,
            'number_of_entries': 12,
            'period': '1',
            'computation_method': 'no_prorata',
            'company_id': cls.company.id,
            'original_value': 12000.0,
            'first_recognition_date': date.today(),
        })

    def test_compute_total_modify_value(self):
        self.asset._compute_total_modify_value()
        self.assertEqual(self.asset.total_modify_value, self.asset.total_value - self.asset.not_depreciable_value + self.asset.gross_value)

    def test_compute_entries_count(self):
        self.asset._compute_entries_count()
        self.assertEqual(self.asset.entries_count, 0)

    def test_onchange_computation_method(self):
        self.asset.computation_method = 'constant_period'
        self.asset._onchange_computation_method()
        self.assertEqual(self.asset.prorata_date, self.asset.first_recognition_date)
        
        self.asset.computation_method = 'no_prorata'
        self.asset._onchange_computation_method()
        self.assertFalse(self.asset.prorata_date)

    def test_action_running(self):
        self.asset.action_running()
        self.assertEqual(self.asset.state, 'running')

    def test_action_close(self):
        self.asset.action_close()
        self.assertEqual(self.asset.state, 'close')

    def test_action_save_template(self):
        result = self.asset.action_save_template()
        self.assertEqual(result.get('res_model'), 'account.asset.type')

    def test_action_get_entries(self):
        result = self.asset.action_get_entries()
        self.assertEqual(result.get('res_model'), 'account.move')
        self.assertEqual(result.get('domain'), [('asset_id', '=', self.asset.id)])

    def test_unlink_draft(self):
        asset = self.Asset.create({
            'name': 'Temp Asset',
            'journal_id': self.journal.id,
            'account_id': self.account.id,
            'expense_account_id': self.expense_account.id,
            'state': 'draft'
        })
        asset.unlink()
        self.assertFalse(self.Asset.search([('id', '=', asset.id)]))

    def test_unlink_running(self):
        self.asset.state = 'running'
        with self.assertRaises(UserError):
            self.asset.unlink()
