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

from odoo.tests import common


class TestAccountJournal(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.account_journal = cls.env['account.journal'].create({
            'name': 'MISC',
            'code': 'MSC',
            'type': 'bank',
        })
        cls.partner = cls.env['res.partner'].create({
            'name': 'Test partner'
        })
        cls.pay = cls.env['account.payment.method'].search([
            ('code', '=', 'credit_payment'), ('payment_type', '=', 'inbound')])
        cls.account_move = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'state': 'draft',
            'partner_id': cls.partner.id,
            'invoice_date': date.today(),
            'invoice_origin': 'FS00003',
            'invoice_line_ids': [(0, 0, {
                'name': "Field Service",
                'quantity': 1,
                'price_unit': 100,
            })]
        })
        cls.account_move.action_post()
        cls.acc_pay_reg = cls.env['account.payment.register'].with_context(
            active_ids=cls.account_move.ids, active_model='account.move'
        ).create({'payment_date': date.today()})
        cls.acc_pay = cls.env['account.payment'].create({
            'journal_id': cls.account_journal.id,
            'payment_type': 'inbound',
            'amount': 111,
            'partner_id': cls.partner.id,
            'partner_type': 'customer',
        })

    def test_default_outbound_payment_methods(self):
        res = self.account_journal._default_outbound_payment_methods().mapped(
            'name')
        self.assertTrue(res.index('Credit'))

    def test_prepare_account_move_vals(self):
        res = self.acc_pay_reg._prepare_account_move_vals(self.acc_pay)
        self.assertEqual(res['move_type'], 'entry')
        self.assertEqual(res['journal_id'], self.account_journal.id)

    def test_prepare_move_line_vals(self):
        account = self.env['account.account'].search(
            [('account_type', '=', 'income')], limit=1
        )

        acc_mov_line = self.env['account.move.line'].create({
            'move_id': self.account_move.id,
            'name': 'Test Line',
            'quantity': 1,
            'price_unit': 100,
            'account_id': account.id,
        })
        self.assertTrue(self.acc_pay_reg._prepare_move_line_vals(acc_mov_line))

    def test_prepare_counterpart_move_lines_vals(self):
        res = self.acc_pay_reg._prepare_counterpart_move_lines_vals(500, -500)
        self.assertEqual(res['credit'], 500)
        self.assertEqual(res['amount_currency'], -500)

    def test_create_payments(self):
        res = self.acc_pay_reg._create_payments()
        prefix = res.name.split('/')[1]
        self.assertEqual(prefix, str(date.today().year))
