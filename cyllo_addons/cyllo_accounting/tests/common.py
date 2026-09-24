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
from odoo import fields
from odoo.tests.common import TransactionCase


class TestCylloAccounting(TransactionCase):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass()
        cls.company_data = cls.setup_company_data(
            'company_1_data', chart_template=chart_template_ref)
        cls.partner = cls.env['res.partner'].create({
            'name': 'Test Partner'
        })
        cls.product_tem = cls.env['product.product'].create({
            'name': 'Test 1',
        })
        cls.account_move = cls.env['account.move'].create({
            'partner_id': cls.partner.id,
            'move_type': 'out_invoice',
            'state': 'draft',
            'invoice_date': '2023-12-05',
            'amount_residual': 1000,
            'amount_total': 1000,
            'line_ids': [fields.Command.create({
                'product_id': cls.product_tem.id,
                'amount_residual_currency': 100,
            })],
        })
        cls.asset_type = cls.env['account.asset.type'].create({
            'company_id': cls.env.company.id,
            'name': 'Asset type',
            'type': 'revenue',
            'active': True,
            'journal_id': cls.company_data['default_journal_misc'].id,
            'computation_method': 'no_prorata',
            'account_id': cls.company_data['default_account_assets'].id,
            'expense_account_id': cls.company_data['default_account_deferred_expense'].id,
            'number_of_entries': 5,
            'period': '1',
            'currency_id': cls.env.company.currency_id.id,
        })
        cls.account_asset_asset = cls.env['account.asset.asset'].create({
            'name': 'Test Asset',
            'active': True,
            'asset_type_id': cls.asset_type.id,
            'company_id': cls.env.company.id,
            'asset_type': cls.asset_type.type,
            'journal_id': cls.asset_type.journal_id.id,
            'account_id': cls.asset_type.account_id.id,
            'expense_account_id': cls.asset_type.expense_account_id.id,
            'number_of_entries': 5,
            'period': '1',
            'original_value': 100,
            'currency_id': cls.asset_type.currency_id.id,
            'date': fields.Date.today(),
            'first_recognition_date': fields.Date.today(),
            'total_value': 10000,
            'not_depreciable_value': 1000,
            'state': 'draft',
            'computation_method': 'no_prorata',
            'prorata_date': fields.Date.today(),
            'depreciation_move_ids': [fields.Command.create({
                'move_type': 'out_invoice',
                'partner_id': cls.partner.id,
                'invoice_date': '2020-01-10',
                'asset_amount': 1000,
                'state': 'draft',
                'line_ids': [fields.Command.create({
                    'product_id': cls.product_tem.id,
                })],
            })]
        })
        cls.payment = cls.env['account.payment'].create({
            'amount': 10.0,
            'payment_type': 'outbound',
            'partner_type': 'customer',
            'partner_id': cls.partner.id,
            'move_ids': cls.account_move.ids,
            'payment_line_ids': [fields.Command.create({
                'move_id': cls.account_move.id,
                'paid_amount': 10.0
            })]
        })

    @classmethod
    def setup_company_data(cls, company_name, chart_template=None, **kwargs):
        """Create a new company having the name passed as parameter. A chart
        of accounts will be installed to this company: the same as the current
        company one. The current user will get access to this company.
        :param chart_template: The chart template is to be used in this new
         company.
        :param company_name: The name of the company.
        :return: A dictionary will be returned containing all relevant
         accounting data for testing.
        """
        company = cls.env.company
        cls.env.user.company_ids |= company
        # Install the chart template
        chart_template = chart_template or cls.env[
            'account.chart.template']._guess_chart_template(company.country_id)
        cls.env['account.chart.template'].try_loading(chart_template,
                                                      company=company,
                                                      install_demo=False)
        if not company.account_fiscal_country_id:
            company.account_fiscal_country_id = cls.env.ref('base.us')
        # The currency could be different after the installation of the chart
        # template.
        if kwargs.get('currency_id'):
            company.write({'currency_id': kwargs['currency_id']})
        return {
            'company': company,
            'currency': company.currency_id,
            'default_account_revenue': cls.env['account.account'].search([
                ('company_id', '=', company.id),
                ('account_type', '=', 'income'),
                ('id', '!=',
                 company.account_journal_early_pay_discount_gain_account_id.id)
            ], limit=1),
            'default_account_expense': cls.env['account.account'].search([
                ('company_id', '=', company.id),
                ('account_type', '=', 'expense'),
                ('id', '!=',
                 company.account_journal_early_pay_discount_loss_account_id.id)
            ], limit=1),
            'default_account_receivable': cls.env['ir.property'].with_company(
                company)._get(
                'property_account_receivable_id', 'res.partner'),
            'default_account_payable': cls.env['account.account'].search([
                ('company_id', '=', company.id),
                ('account_type', '=', 'liability_payable')], limit=1),
            'default_account_assets': cls.env['account.account'].search([
                ('company_id', '=', company.id),
                ('account_type', '=', 'asset_fixed')], limit=1),
            'default_account_deferred_expense': cls.env[
                'account.account'].search([
                ('company_id', '=', company.id),
                ('account_type', '=', 'asset_current')], limit=1),
            'default_account_deferred_revenue': cls.env[
                'account.account'].search([
                ('company_id', '=', company.id),
                ('account_type', '=', 'liability_current')], limit=1),
            'default_account_tax_sale': company.account_sale_tax_id.mapped(
                'invoice_repartition_line_ids.account_id'),
            'default_account_tax_purchase': company.account_purchase_tax_id.mapped(
                'invoice_repartition_line_ids.account_id'),
            'default_journal_misc': cls.env['account.journal'].search([
                ('company_id', '=', company.id),
                ('type', '=', 'general')], limit=1),
            'default_journal_sale': cls.env['account.journal'].search([
                ('company_id', '=', company.id),
                ('type', '=', 'sale')], limit=1),
            'default_journal_purchase': cls.env['account.journal'].search([
                ('company_id', '=', company.id),
                ('type', '=', 'purchase')], limit=1),
            'default_journal_bank': cls.env['account.journal'].search([
                ('company_id', '=', company.id),
                ('type', '=', 'bank')], limit=1),
            'default_journal_cash': cls.env['account.journal'].search([
                ('company_id', '=', company.id),
                ('type', '=', 'cash')], limit=1),
            'default_tax_sale': company.account_sale_tax_id,
            'default_tax_purchase': company.account_purchase_tax_id,
        }

class TestCylloAccountingFiscalYear(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({
            'name': 'Test partner'
        })
        cls.fiscal_year = cls.env['account.fiscal.year'].create({
            'name': 'Year1',
            'start_date': '2021-01-01',
            'end_date': '2021-12-31',
            'company_id': cls.env.company.id,
            'state': 'draft'
        })
        cls.fiscal_year2 = cls.env['account.fiscal.year'].create({
            'name': 'Year2',
            'start_date': '2026-01-01',
            'end_date': '2026-12-31',
            'company_id': cls.env.company.id,
            'state': 'draft',
        })
        cls.fiscal_year3 = cls.env['account.fiscal.year'].create({
            'name': 'Year2',
            'start_date': '2022-01-01',
            'end_date': '2022-12-31',
            'company_id': cls.env.company.id,
            'state': 'draft',
        })
        cls.account_move = cls.env['account.move'].create({
            'partner_id': cls.partner.id,
            'move_type': 'out_invoice',
            'state': 'draft',
            'invoice_date': '2021-10-05',
            'fiscal_year_id': cls.fiscal_year2.id,
        })