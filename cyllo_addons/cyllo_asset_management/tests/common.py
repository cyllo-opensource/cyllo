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
from datetime import date

from odoo import fields
from odoo.tests import common


class TestCommon(common.TransactionCase):
    """Common test records"""

    @classmethod
    def setUpClass(cls):
        """Set up class values"""
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({'name': 'John'})
        cls.department = cls.env['hr.department'].create({'name': 'HR'})
        cls.employee = cls.env['hr.employee'].create({'name': 'Test Employee'})
        cls.asset_type = cls.env['asset.type'].create({'name': 'Test Asset type'})
        cls.currency_id = cls.env['res.currency'].create({'name': 'Test Coin',
                                                          'symbol': '☺'})
        cls.company = cls.env.company
        cls.product = cls.env.ref("product.product_product_4").id
        cls.account_1 = cls.env['account.account'].create({
            'name': 'account 1',
            'code': 'X2020',
            'account_type': 'asset_fixed',
        })
        cls.account_3 = cls.env['account.account'].create({
            'name': 'account 1',
            'code': 'er52',
            'account_type': 'expense',
        })
        cls.asset_journal_id = cls.env['account.journal'].create({'name': 'awesome journal',
                                                                  'type': 'general',
                                                                  'code': 'AJ'})
        cls.item_id = cls.env['asset.item'].create({
            'name': 'test item',
            'asset_type_id': cls.asset_type.id,
            'purchase_date': '5000-5-6',
            'fixed_asset_account_id': cls.account_1.id,
            'asset_depreciation_account_id': cls.account_1.id,
            'asset_expense_account_id': cls.account_3.id,
            'asset_journal_id': cls.asset_journal_id.id,
            'depreciation_method': 'straight_line',
        })
        cls.account_2 = cls.env['account.account'].create({
            'name': 'account 1',
            'code': 'X2025',
            'account_type': 'asset_fixed',
            'multiple_asset': True,
            'asset_model_id': cls.item_id.id,
        })
        cls.depreciation_line = cls.env['asset.depreciation.line'].create({'year': 8120,
                                                                           'date': fields.date.today(),
                                                                           'company_id': cls.company.id})
        cls.account_move = cls.env['account.move'].create({
            'name': 'TestInv01',
            'partner_id': cls.partner.id,
            'move_type': 'out_invoice',
            'state': 'draft',
            'invoice_date': date.today(),
            'depreciation_line_id': cls.depreciation_line.id,
            'line_ids': [(fields.Command.create({
                'name': 'Test move line',
                'product_id': cls.env.ref("product.product_product_4").id,
                'quantity': 2,
                'account_id': cls.account_2.id,
            }))]
        })
        cls.asset = cls.env['asset.asset'].create({
            'name': 'ABC',
            'asset_item_id': cls.item_id.id,
            'asset_type_id': cls.asset_type.id,
            'original_value': 2,
            'salvage_value': 2,
            'is_depreciate': True,
            'status': 'draft',
            'depreciation_method': 'straight_line',
            'computation_method': 'no_prorata',
        })
        cls.account_move.asset_asset_id = cls.asset.id
        cls.asset_rental = cls.env['asset.rental'].create({
            'asset_id': cls.asset.id,
            'start_date': '6511-5-7',
            'end_date': '6511-5-9',
            'status': 'rent',
            'customer_id': cls.partner.id,
            'company_id': cls.company.id,
            'payment_terms': 'day',
            'payment_type': 'complete',
        })
        cls.asset_maintenance = cls.env['account.asset.maintenance'].create({
            'asset_id': cls.asset.id,
            'company_id': cls.company.id,
            'status': 'new',
        })
        cls.asset_repair = cls.env['account.asset.repair'].create({
            'asset_id': cls.asset.id,
            'company_id': cls.company.id,
            'status': 'new',
        })
        cls.reserved_asset = cls.env['asset.reservation'].create({
            'asset_id': cls.asset.id,
            'start_date': '6511-5-7',
            'end_date': '6511-5-9',
            'status': 'reserve',
            'employee_id': cls.employee.id,
            'company_id': cls.company.id,
        })
        cls.brand = cls.env['asset.brand'].create({
            'name': 'XYZ Asset Brand',
            'company_id': cls.company.id,
        })
