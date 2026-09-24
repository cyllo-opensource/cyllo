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


class TestAccountPdcPaymentRegister(TestCylloAccountingPdc):

    def test_get_batch_communication(self):
        self.assertTrue(self.payment_register._get_batch_communication(
            self.batch_result))
        self.assertIn('Customer Payment', self.payment_register._get_batch_communication(
            self.batch_result))

    def test_get_batch_available_journals(self):
        self.assertTrue(self.payment_register._get_batch_available_journals(
                  self.batch_result))
        
    def test_get_batch_journal(self):
        self.assertEqual(self.payment_register._get_batch_journal(
            self.batch_result).type, 'bank')
        
    def test_get_batches(self):
        self.assertTrue(self.payment_register._get_batches())
        
    def test_get_wizard_values_from_batch(self):
        self.assertEqual(self.payment_register._get_wizard_values_from_batch(
            self.batch_result)['payment_type'], 'inbound')
        self.assertEqual(self.payment_register._get_wizard_values_from_batch(
            self.batch_result)['partner_type'], 'customer')
        self.assertEqual(self.payment_register._get_wizard_values_from_batch(
            self.batch_result)['source_currency_id'],
                         self.env.company.currency_id.id)
        self.assertEqual(self.payment_register._get_wizard_values_from_batch(
            self.batch_result)['partner_id'], self.partner.id)

    def test_compute_communication(self):
        self.assertFalse(self.payment_register.communication)

    def test_get_total_amount_using_same_currency(self):
        self.assertEqual(
            self.payment_register._get_total_amount_using_same_currency(
                self.batch_result, True), (100.0, False))
    
    def test_get_total_amount_in_wizard_currency_to_full_reconcile(self):
        self.assertEqual(self.payment_register2._get_total_amount_in_wizard_currency_to_full_reconcile(self.batch_result, True), (0.0, False))

    def test_compute_amount(self):
        self.assertEqual(self.payment_register.amount, 0.0)
        self.assertEqual(self.payment_register2.amount, 100.0)

    def test_default_get(self):
        fields_list = ['line_ids', 'can_edit_wizard', 'can_group_payments',
                       'early_payment_discount_mode', 'payment_type',
                       'partner_type', 'source_amount', 'company_id',
                       'source_amount_currency', 'source_currency_id',
                       'partner_id', 'country_code', 'currency_id',
                       'available_journal_ids', 'company_currency_id',
                       'available_payment_method_line_ids', 'journal_id',
                       'hide_writeoff_section', 'payment_method_line_id',
                       'group_payment', 'bank_name', 'cheque_reference',
                       'amount', 'payment_date', 'due_date', 'communication',
                       'payment_difference', 'payment_difference_handling',
                       'writeoff_account_id', 'writeoff_label']
        self.assertEqual(self.payment_register.default_get(fields_list)[
                             'payment_date'], fields.Date.today())
        self.assertEqual(self.payment_register.default_get(fields_list)[
                             'due_date'], fields.Date.today())
        self.assertEqual(self.payment_register.default_get(fields_list)[
                             'writeoff_label'], 'Write-Off')
        
    def test_create_payment_vals_from_wizard(self):
        self.assertEqual(
            self.payment_register2._create_payment_vals_from_wizard(
                self.batch_result)['bank_name'], 'ABCD Bank')
        self.assertEqual(
            self.payment_register2._create_payment_vals_from_wizard(
                self.batch_result)['cheque_reference'], 'Reference')
        self.assertEqual(
            self.payment_register2._create_payment_vals_from_wizard(
                self.batch_result)['amount'], 100)
        self.assertEqual(
            self.payment_register2._create_payment_vals_from_wizard(
                self.batch_result)['payment_type'], 'inbound')
        self.assertEqual(
            self.payment_register2._create_payment_vals_from_wizard(
                self.batch_result)['partner_type'], 'customer')
        
    def test_create_payment_vals_from_batch(self):
        self.assertEqual(
            self.payment_register._create_payment_vals_from_batch(
                self.batch_result)['partner_type'], 'customer')
        self.assertEqual(
            self.payment_register._create_payment_vals_from_batch(
                self.batch_result)['payment_type'], 'inbound')

    def test_init_payments(self):
        self.assertTrue(self.payment_register._init_payments(self.to_process))
        self.assertEqual(self.payment_register._init_payments(self.to_process)
                         ['bank_name'], 'Bank')
        self.assertEqual(self.payment_register._init_payments(self.to_process)
                         ['cheque_reference'], 'Chk Ref')
        self.assertEqual(self.payment_register._init_payments(self.to_process)
                         ['payment_type'], 'inbound')
        self.assertEqual(self.payment_register._init_payments(self.to_process)
                         ['partner_type'], 'customer')
