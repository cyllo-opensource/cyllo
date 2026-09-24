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


class ProductCategory(models.Model):
    _inherit = "product.category"

    property_valuation = fields.Selection([
        ('manual_periodic', 'Manual'),
        ('real_time', 'Automated')
    ], string='Inventory Valuation', required=True, default='manual_periodic')

    property_stock_valuation_account_id = fields.Many2one(
        'account.account', 'Stock Valuation Account',
        company_dependent=True,
        domain="[('deprecated', '=', False)]",
        check_company=True)

    property_stock_account_input_categ_id = fields.Many2one(
        'account.account', 'Stock Input Account',
        company_dependent=True,
        domain="[('deprecated', '=', False)]",
        check_company=True)

    property_stock_account_output_categ_id = fields.Many2one(
        'account.account', 'Stock Output Account',
        company_dependent=True,
        domain="[('deprecated', '=', False)]",
        check_company=True)

    property_stock_journal = fields.Many2one(
        'account.journal', 'Stock Journal',
        company_dependent=True,
        check_company=True)

    @api.onchange('property_valuation')
    def _onchange_property_valuation(self):
        """Preserve field values when changing valuation method"""
        if self.property_valuation == 'real_time':
            # Ensure the required fields for automated valuation are visible and maintained
            if not self.property_stock_valuation_account_id:
                self.property_stock_valuation_account_id = self._get_default_property_account(
                    'property_stock_valuation_account_id')
            if not self.property_stock_account_input_categ_id:
                self.property_stock_account_input_categ_id = self._get_default_property_account(
                    'property_stock_account_input_categ_id')
            if not self.property_stock_account_output_categ_id:
                self.property_stock_account_output_categ_id = self._get_default_property_account(
                    'property_stock_account_output_categ_id')
            if not self.property_stock_journal:
                self.property_stock_journal = self._get_default_property_journal()

    def _get_default_property_account(self, property_field):
        """Get default account from ir.property"""
        ir_property = self.env['ir.property'].sudo()
        company_id = self.env.company.id
        prop = ir_property.search([
            ('name', '=', property_field),
            ('company_id', '=', company_id),
            ('res_id', '=', False)
        ], limit=1)
        if prop and prop.value_reference:
            account_id = int(prop.value_reference.split(',')[1])
            return self.env['account.account'].browse(account_id)
        return False

    def _get_default_property_journal(self):
        """Get default stock journal from ir.property"""
        ir_property = self.env['ir.property'].sudo()
        company_id = self.env.company.id
        prop = ir_property.search([
            ('name', '=', 'property_stock_journal'),
            ('company_id', '=', company_id),
            ('res_id', '=', False)
        ], limit=1)
        if prop and prop.value_reference:
            journal_id = int(prop.value_reference.split(',')[1])
            return self.env['account.journal'].browse(journal_id)
        return False

    @api.model
    def create(self, vals):
        """Ensure properties are properly set on creation"""
        category = super().create(vals)
        if category.property_valuation == 'real_time':
            # Force compute of related fields
            category._onchange_property_valuation()
        return category

    def write(self, vals):
        """Ensure properties are maintained on write"""
        res = super().write(vals)
        if 'property_valuation' in vals and vals[
            'property_valuation'] == 'real_time':
            for category in self:
                category._onchange_property_valuation()
        return res
