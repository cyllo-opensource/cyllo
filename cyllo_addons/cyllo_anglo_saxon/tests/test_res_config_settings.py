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


class TestResConfigSettings(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Settings = cls.env['res.config.settings']
        cls.IrProperty = cls.env['ir.property']
        cls.Account = cls.env['account.account']
        cls.Journal = cls.env['account.journal']
        cls.Company = cls.env.company

        # Minimal accounts (safe types)
        cls.income_account = cls.Account.create({
            'name': 'Test Income',
            'code': 'TINCOME',
            'account_type': 'income',
            'company_id': cls.Company.id,
        })

        cls.expense_account = cls.Account.create({
            'name': 'Test Expense',
            'code': 'TEXPENSE',
            'account_type': 'expense',
            'company_id': cls.Company.id,
        })

        cls.stock_account = cls.Account.create({
            'name': 'Stock Valuation',
            'code': 'TSTOCK',
            'account_type': 'asset_current',
            'company_id': cls.Company.id,
        })

        cls.stock_journal = cls.Journal.create({
            'name': 'Stock Journal',
            'code': 'STK',
            'type': 'general',
            'company_id': cls.Company.id,
        })

    # ---------------------------------------------------------
    # TEST 01: Account domain excludes unwanted account types
    # ---------------------------------------------------------
    def test_01_get_account_domain(self):
        domain = self.Settings._get_account_domain()

        self.assertIn(('deprecated', '=', False), domain)
        self.assertIn(
            ('account_type', 'not in', [
                'asset_receivable',
                'liability_payable',
                'asset_cash',
                'liability_credit_card',
                'off_balance'
            ]),
            domain
        )

    # ---------------------------------------------------------
    # TEST 02: default_get reads ir.property values
    # ---------------------------------------------------------
    def test_02_default_get_reads_properties(self):
        self.IrProperty._set_default(
            'property_account_income_categ_id',
            'product.category',
            self.income_account,
            self.Company
        )

        self.IrProperty._set_default(
            'property_account_expense_categ_id',
            'product.category',
            self.expense_account,
            self.Company
        )

        res = self.Settings.default_get([
            'property_account_income_categ_id',
            'property_account_expense_categ_id'
        ])

        self.assertEqual(
            res['property_account_income_categ_id'],
            self.income_account.id
        )
        self.assertEqual(
            res['property_account_expense_categ_id'],
            self.expense_account.id
        )

    # ---------------------------------------------------------
    # TEST 03: onchange disables automatic stock accounting
    # ---------------------------------------------------------
    def test_03_onchange_module_cyllo_anglo_saxon(self):
        settings = self.Settings.create({
            'module_cyllo_anglo_saxon': False,
        })

        settings._onchange_module_cyllo_anglo_saxon()

        self.assertFalse(settings.group_stock_accounting_automatic)

    # ---------------------------------------------------------
    # TEST 04: set_values stores ir.property defaults
    # ---------------------------------------------------------
    def test_04_set_values_sets_properties(self):
        settings = self.Settings.create({
            'module_cyllo_anglo_saxon': True,
            'property_account_income_categ_id': self.income_account.id,
            'property_account_expense_categ_id': self.expense_account.id,
            'property_stock_valuation_account_id': self.stock_account.id,
            'property_stock_journal': self.stock_journal.id,
        })

        settings.set_values()

        prop = self.IrProperty.search([
            ('name', '=', 'property_account_income_categ_id'),
            ('company_id', '=', self.Company.id),
            ('res_id', '=', False),
        ], limit=1)

        self.assertTrue(prop)
        self.assertIn(
            str(self.income_account.id),
            prop.value_reference
        )
