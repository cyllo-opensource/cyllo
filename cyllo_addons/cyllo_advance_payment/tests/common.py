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


class TestCylloAdvancePayment(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
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
        cls.payment = cls.env['account.payment'].create({
            'name': 'Test Payment',
            'payment_type': 'outbound',
            'amount': 10.0,
            'partner_type': 'customer',
            'partner_id': cls.partner.id,
            'journal_id': cls.account_journal.id
        })
        cls.payment2 = cls.env['account.payment'].create({
            'name': 'Test Payment2',
            'payment_type': 'outbound',
            'amount': 50.0,
            'partner_type': 'customer',
            'partner_id': cls.partner.id,
            'journal_id': cls.account_journal.id
        })
        cls.product_a = cls.env['product.product'].create({
            'name': 'p1',
            'company_id': cls.env.company.id,
            'list_price': 100.0,
        })
        cls.purchase1 = cls.env['purchase.order'].create({
            'partner_id': cls.partner.id,
            'advance_payment_ids': [cls.payment.id, cls.payment2.id],
            'order_line': [
                (fields.Command.create({
                    'product_id': cls.product_a.id,
                    'product_qty': 2.0,
                }))],
        })
        cls.sale_order = cls.env['sale.order'].create({
            'partner_id': cls.partner.id,
            'advance_payment_ids': [cls.payment.id, cls.payment2.id],
            'order_line': [
                (fields.Command.create({
                    'product_id': cls.product_a.id,
                    'product_uom_qty': 2.0,
                }))],
        })
