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
from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    property_account_expense_categ_id = fields.Many2one(
        'account.account', "Expense Account",
        check_company=True,
        domain=lambda self: self._get_account_domain())
    property_account_income_categ_id = fields.Many2one(
        'account.account', "Income Account",
        check_company=True,
        domain=lambda self: self._get_account_domain())
    property_stock_valuation_account_id = fields.Many2one(
        'account.account', "Stock Valuation Account",
        check_company=True,
        domain="[('deprecated', '=', False)]")
    property_stock_account_input_categ_id = fields.Many2one(
        'account.account', "Stock Input Account",
        check_company=True,
        domain="[('deprecated', '=', False)]")
    property_stock_account_output_categ_id = fields.Many2one(
        'account.account', "Stock Output Account",
        check_company=True,
        domain="[('deprecated', '=', False)]")
    property_stock_journal = fields.Many2one(
        'account.journal', "Stock Journal",
        check_company=True)

    @api.model
    def _get_account_domain(self):
        excluded_types = [
            'asset_receivable',
            'liability_payable',
            'asset_cash',
            'liability_credit_card',
            'off_balance'
        ]
        return [
            ('deprecated', '=', False),
            ('account_type', 'not in', excluded_types)
        ]

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)

        if 'module_cyllo_anglo_saxon' in res and not res.get(
                'module_cyllo_anglo_saxon'):
            res['group_stock_accounting_automatic'] = False

        property_fields = [
            'property_stock_journal',
            'property_account_income_categ_id',
            'property_account_expense_categ_id',
            'property_stock_valuation_account_id',
            'property_stock_account_input_categ_id',
            'property_stock_account_output_categ_id',
        ]

        properties = self.env['ir.property'].sudo().search([
            ('name', 'in', property_fields),
            ('company_id', '=', self.env.company.id),
            ('res_id', '=', False),
        ])

        property_values = {
            prop.name: prop.value_reference
            for prop in properties
            if prop.value_reference
        }

        for field, value_ref in property_values.items():
            model, record_id = value_ref.split(',')
            if record := self.env[model].browse(int(record_id)).exists():
                res[field] = record.id

        return res

    @api.onchange('module_cyllo_anglo_saxon')
    def _onchange_module_cyllo_anglo_saxon(self):
        if not self.module_cyllo_anglo_saxon:
            self.group_stock_accounting_automatic = False

    def set_values(self):
        super().set_values()

        if not self.module_cyllo_anglo_saxon:
            self.env['ir.config_parameter'].sudo().set_param(
                'stock.group_stock_accounting_automatic', 'False')

        field_list = [
            'property_stock_journal',
            'property_account_income_categ_id',
            'property_account_expense_categ_id',
            'property_stock_valuation_account_id',
            'property_stock_account_input_categ_id',
            'property_stock_account_output_categ_id',
        ]
        for field in field_list:
            self.env['ir.property']._set_default(
                field,
                'product.category',
                self[field],
                self.company_id,
            )
