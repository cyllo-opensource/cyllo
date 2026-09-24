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


class TestGeneralLedgerReport(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Report = cls.env['report.cyllo_accounting.general_ledger']
        cls.Account = cls.env['account.account']
        cls.Company = cls.env.company

    # ---------------------------------------------------------
    # TEST 01: _get_data returns empty list safely
    # ---------------------------------------------------------
    def test_01_get_data_empty_result(self):
        # Create a minimal account (safe: no posting)
        account = self.Account.create({
            "name": "Test GL Account",
            "code": "GLTEST01",
            "account_type": "asset_current",
            "company_id": self.Company.id,
        })

        data = self.Report._get_data(
            account.id,
            target_move=['posted'],
            analytic_ids=[],
            journal_ids=[],
            company_ids=[self.Company.id],
            start_date='2000-01-01',
            end_date='2100-01-01',
        )

        self.assertIsInstance(data, list)
        self.assertEqual(data, [])

    # ---------------------------------------------------------
    # TEST 02: _get_data accepts multiple filter arguments
    # ---------------------------------------------------------
    def test_02_get_data_with_multiple_filters(self):
        account = self.Account.create({
            "name": "Test GL Account 2",
            "code": "GLTEST02",
            "account_type": "asset_current",
            "company_id": self.Company.id,
        })

        data = self.Report._get_data(
            account.id,
            target_move=['draft', 'posted'],
            analytic_ids=[1, 2],
            journal_ids=[1],
            company_ids=[self.Company.id],
            start_date='2000-01-01',
            end_date='2100-01-01',
        )

        self.assertIsInstance(data, list)

    # ---------------------------------------------------------
    # TEST 03: Returned keys structure (if rows exist)
    # ---------------------------------------------------------
    def test_03_get_data_keys_structure(self):
        account = self.Account.create({
            "name": "Test GL Account 3",
            "code": "GLTEST03",
            "account_type": "asset_current",
            "company_id": self.Company.id,
        })

        data = self.Report._get_data(
            account.id,
            target_move=['posted'],
            start_date='2000-01-01',
            end_date='2100-01-01',
        )

        if data:
            row = data[0]
            expected_keys = {
                'id', 'annotations', 'account_id', 'credit',
                'date', 'debit', 'journal_id', 'move_id',
                'move_name', 'name', 'partner_name', 'partner_id'
            }

            self.assertTrue(expected_keys.issubset(row.keys()))
