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
from odoo.tests import common
from datetime import timedelta


class TestCylloAccountingPdc(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_data = cls.setup_company_data('company_1_data')

        cls.account_journal = cls.env['account.journal'].create({
            'name': 'Test Bank',
            'type': 'bank',
            'company_id': cls.env.company.id,
            'code': 'BNKT',
            'sequence': 10,
            'currency_id': cls.env.company.currency_id.id
        })
        cls.partner = cls.env['res.partner'].create({
            'name': 'Partner A'
        })
        cls.account_move = cls.env['account.move'].create({
            'partner_id': cls.partner.id,
            'move_type': 'out_invoice',
            'state': 'draft',
            'invoice_line_ids': [
                (fields.Command.create({
                    'name': 'Test Line',
                    'price_unit': 100,
                    'account_id': cls.company_data[
                        'default_account_deferred_expense'].id
                }))
            ]
        })
        cls.pdc_payment = cls.env['account.pdc.payment'].create({
            'move_id': cls.account_move.id,
            'payment_type': 'inbound',
            'amount': 100,
            'currency_id': cls.env.company.currency_id.id,
            'partner_type': 'customer',
            'payment_status': 'draft',
            'partner_id': cls.partner.id,
            'bank_name': 'ABCD Bank',
            'cheque_reference': 'Check1',
            'due_date': fields.Date.today(),
        })
        cls.pdc_payment2 = cls.env['account.pdc.payment'].create({
            'move_id': cls.account_move.id,
            'payment_type': 'outbound',
            'payment_reference': 'Test Ref',
            'amount': 100,
            'currency_id': cls.env.company.currency_id.id,
            'partner_type': 'customer',
            'payment_status': 'draft',
            'partner_id': cls.partner.id,
            'bank_name': 'ABCD Bank',
            'cheque_reference': 'Check2',
            'due_date': fields.Date.today(),
        })
        cls.pdc_payment3 = cls.env['account.pdc.payment'].create({
            'move_id': cls.account_move.id,
            'amount': 100,
            'currency_id': cls.env.company.currency_id.id,
            'partner_type': 'customer',
            'payment_status': 'draft',
            'partner_id': cls.partner.id,
            'bank_name': 'ABCD Bank',
            'cheque_reference': 'Check2',
            'due_date': fields.Date.today(),
        })
        cls.payment_register = cls.env['account.pdc.payment.register'].with_context(
            active_model='account.move', active_ids=cls.create_invoice().ids).create({
                'payment_date': fields.Date.today(),
                'due_date': fields.Date.today(),
                'bank_name': 'ABCD Bank',
                'cheque_reference': 'Reference',
                'can_edit_wizard': True,
                'line_ids': cls.account_move.line_ids.ids,
                'partner_type': 'supplier',
            })
        cls.payment_register2 = cls.env[
            'account.pdc.payment.register'].with_context(
            active_model='account.move',
            active_ids=cls.create_invoice().ids).create({
                'payment_date': fields.Date.today(),
                'due_date': fields.Date.today(),
                'currency_id': cls.env.company.currency_id.id,
                'bank_name': 'ABCD Bank',
                'cheque_reference': 'Reference',
                'can_edit_wizard': True,
                'amount': 100
            })
        cls.batch_result = {
            'lines': cls.account_move.line_ids,
            'payment_values': {
                'partner_id': cls.partner.id,
                'account_id': cls.company_data['default_account_revenue'],
                'partner_bank_id': 'AAAA',
                'partner_type': 'customer',
                'currency_id': cls.env.company.currency_id.id,
                'payment_type': 'inbound'}}
        payment_method_line = cls.account_journal._get_available_payment_method_lines(
            'inbound').filtered(lambda x: x.code == 'pdc_payment')
        cls.to_process = [{
            'create_vals': {'date': fields.Date.today(),
                            'due_date': fields.Date.today(),
                            'bank_name': 'Bank', 'cheque_reference': 'Chk Ref',
                            'amount': 2068.85, 'payment_type': 'inbound',
                            'partner_type': 'customer',
                            'ref': 'INV/2024/00008',
                            'journal_id': cls.account_journal.id,
                            'company_id': cls.env.company.id,
                            'currency_id': cls.env.company.currency_id.id,
                            'partner_id': cls.partner.id,
                            'payment_method_line_id': payment_method_line.id}, }]

    @classmethod
    def create_invoice(cls):
        account_move = cls.env['account.move'].create({
            'partner_id': cls.partner.id,
            'move_type': 'out_invoice',
            'state': 'draft',
            'invoice_date': fields.Date.today(),
            'payment_state': 'not_paid',
            'invoice_date_due': fields.Date.today() + timedelta(days=2),
            'line_ids': [fields.Command.create({
                'name': 'Prod',
                'quantity': 1,
                'price_unit': 100
            })]})
        account_move.action_post()
        return account_move

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

