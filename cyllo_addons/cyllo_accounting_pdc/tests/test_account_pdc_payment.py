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
from odoo.addons.cyllo_accounting_pdc.tests.common import TestCylloAccountingPdc


class TestAccountPdcPayment(TestCylloAccountingPdc):

    def test_compute_pdc_move_count(self):
        self.account_move = self.env['account.move'].create({
            'partner_id': self.partner.id,
            'move_type': 'out_invoice',
            'state': 'draft',
            'pdc_payment_id': self.pdc_payment.id,
            'invoice_line_ids': [
                (fields.Command.create({
                    'name': 'Test Line',
                    'price_unit': 100,
                    'account_id': self.company_data['default_account_revenue'].id,
                }))
            ]
        })
        self.assertGreaterEqual(self.pdc_payment.pdc_move_count, 1)

    def test_compute_pdc_account_id(self):
        self.assertEqual(self.pdc_payment.pdc_account_id.name, 'PDC Payment')

    def test_compute_outstanding_account_id(self):
        self.assertEqual(self.pdc_payment.outstanding_account_id.name,
                         'Outstanding Receipts')
        self.assertEqual(self.pdc_payment2.outstanding_account_id.name,
                         'Outstanding Payments')

    def test_compute_payment_method_line_id(self):
        self.pdc_payment._compute_payment_method_line_id()
        self.assertTrue(self.pdc_payment.payment_method_line_id)
        
    def test_compute_currency_id(self):
        self.assertTrue(self.pdc_payment.currency_id)

    def test_action_post(self):
        self.pdc_payment.action_post()
        self.assertEqual(self.pdc_payment.payment_status, 'registered')
    
    def test_action_done(self):
        self.pdc_payment.action_done()
        self.assertEqual(self.pdc_payment.payment_status, 'posted')

    def test_action_deposit(self):
        self.pdc_payment.action_post()
        self.pdc_payment.action_deposit()
        self.assertEqual(self.pdc_payment.payment_status, 'registered')
        
    def test_action_cancel(self):
        self.pdc_payment.action_cancel()
        self.assertEqual(self.pdc_payment.payment_status, 'cancelled')
        
    def test_action_draft(self):
        account_move = self.env['account.move'].create({
            'partner_id': self.partner.id,
            'move_type': 'out_invoice',
            'state': 'cancel',
            'invoice_line_ids': [
                (fields.Command.create({
                    'name': 'Test Line',
                    'price_unit': 100,
                    'account_id': self.company_data['default_account_revenue'].id,
                }))
            ]
        })
        pdc_payment3 = self.env['account.pdc.payment'].create({
            'move_id': account_move.id,
            'amount': 100,
            'currency_id': self.env.company.currency_id.id,
            'partner_type': 'customer',
            'payment_status': 'cancelled',
            'partner_id': self.partner.id,
            'bank_name': 'ABCD Bank',
            'cheque_reference': 'Check2',
            'due_date': fields.Date.today(),
        })
        pdc_payment3.action_draft()
        self.assertEqual(pdc_payment3.payment_status, 'draft')
        
    def test_seek_for_lines(self):
        account_type = []
        if 'asset_receivable' in self.pdc_payment._seek_for_lines()[1].mapped('account_type'):
            account_type.append(True)
        self.assertTrue(account_type[0])

    def test_get_aml_default_display_name_list(self):
        date = fields.Date.today().strftime("%m/%d/%Y")
        self.assertEqual(self.pdc_payment._get_aml_default_display_name_list(),
                         [('label', 'Customer Payment'), ('sep', ' '),
                          ('amount', '$\xa0100.00'), ('sep', ' - '),
                          ('partner', 'Partner A'), ('sep', ' - '),
                          ('date', date)])

    def test_get_liquidity_aml_display_name_list(self):
        date = fields.Date.today().strftime("%m/%d/%Y")
        self.assertEqual(
            self.pdc_payment._get_liquidity_aml_display_name_list(),
            [('label', 'Customer Payment'), ('sep', ' '),
             ('amount', '$\xa0100.00'), ('sep', ' - '),
             ('partner', 'Partner A'), ('sep', ' - '), ('date', date)])
        self.assertEqual(
            self.pdc_payment2._get_liquidity_aml_display_name_list(),
            [('reference', 'Test Ref')])
        
    def test_prepare_move_line_default_vals(self):
        # Inbound payment without reference given
        date = fields.Date.today().strftime("%m/%d/%Y")
        self.assertEqual(
            self.pdc_payment._prepare_move_line_default_vals()[0]['name'],
            f'Customer Payment $\xa0100.00 - Partner A - {date}')
        self.assertEqual(self.pdc_payment._prepare_move_line_default_vals()[0][
                             'date_maturity'], fields.Date.today())
        self.assertEqual(self.pdc_payment._prepare_move_line_default_vals()[0][
                             'amount_currency'], 100)
        self.assertEqual(self.pdc_payment._prepare_move_line_default_vals()[0][
                             'debit'], 100)
        self.assertEqual(self.pdc_payment._prepare_move_line_default_vals()[0][
                             'credit'], 0)
        self.assertEqual(self.pdc_payment._prepare_move_line_default_vals()[1][
                             'amount_currency'], -100)
        self.assertEqual(self.pdc_payment._prepare_move_line_default_vals()[1][
                             'debit'], 0)
        self.assertEqual(self.pdc_payment._prepare_move_line_default_vals()[1][
                             'credit'], 100)
        # Outbound payment with reference given
        self.assertEqual(self.pdc_payment2._prepare_move_line_default_vals()[0]
                         ['name'], 'Test Ref')
        self.assertEqual(self.pdc_payment2._prepare_move_line_default_vals()[0]
                         ['date_maturity'], fields.Date.today())
        self.assertEqual(self.pdc_payment2._prepare_move_line_default_vals()[0]
                         ['amount_currency'], -100)
        self.assertEqual(self.pdc_payment2._prepare_move_line_default_vals()[0]
                         ['debit'], 0)
        self.assertEqual(self.pdc_payment2._prepare_move_line_default_vals()[0]
                         ['credit'], 100)
        self.assertEqual(self.pdc_payment2._prepare_move_line_default_vals()[1]
                         ['amount_currency'], 100)
        self.assertEqual(self.pdc_payment2._prepare_move_line_default_vals()[1]
                         ['debit'], 100)
        self.assertEqual(self.pdc_payment2._prepare_move_line_default_vals()[1]
                         ['credit'], 0)
        
    def test_create(self):
        vals_list = [{'payment_status': 'draft', 'partner_type': 'customer',
                      'company_id': self.env.company.id,
                      'payment_type': 'inbound', 'partner_id': self.partner.id,
                      'amount': 10, 'date': fields.Date.today(), 'ref': 'Memo',
                      'journal_id': self.account_move.journal_id.id,
                      'due_date': fields.Date.today(), 'bank_name': 'BNK ACC',
                      'cheque_reference': 'CHK REF'}]
        pdc_pay = self.pdc_payment2.create(vals_list)
        self.assertTrue(pdc_pay)

    def test_write(self):
        self.assertTrue(self.pdc_payment2.write({'ref': 'Memo01'}))

    def test_unlink(self):
        self.assertTrue(self.pdc_payment.unlink())
