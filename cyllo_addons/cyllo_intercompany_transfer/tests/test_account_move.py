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

from odoo import Command, fields
from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import IntercompanyCommon


@tagged('post_install', '-at_install')
class TestAccountMove(IntercompanyCommon):

    def _create_invoice(self, partner, product=None, qty=2.0, price=50.0):
        return self.env['account.move'].with_company(self.company_a).create({
            'move_type': 'out_invoice',
            'company_id': self.company_a.id,
            'partner_id': partner.id,
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': [Command.create({
                'product_id': (product or self.storable).id,
                'name': 'Line',
                'quantity': qty,
                'price_unit': price,
            })],
        })

    def _bills(self, origin, company=None):
        return self.env['account.move'].sudo().search([
            ('move_type', '=', 'in_invoice'),
            ('invoice_origin', '=', origin),
            ('company_id', '=', (company or self.company_b).id),
        ])

    def test_direct_invoice_creates_vendor_bill(self):
        self._set_params(create_vendor_bills=True)
        invoice = self._create_invoice(self.partner_b, qty=2, price=50)
        invoice.action_post()
        bill = self._bills(invoice.name)
        self.assertEqual(len(bill), 1)
        self.assertEqual(bill.partner_id, self.partner_a)
        self.assertEqual(bill.company_id, self.company_b)
        self.assertEqual(len(bill.invoice_line_ids), 1)
        self.assertEqual(bill.invoice_line_ids.quantity, 2)
        self.assertEqual(bill.invoice_line_ids.price_unit, 50)

    def test_setting_disabled_creates_no_bill(self):
        self._set_params(create_vendor_bills=False)
        invoice = self._create_invoice(self.partner_b)
        invoice.action_post()
        self.assertFalse(self._bills(invoice.name))

    def test_non_intercompany_customer_creates_no_bill(self):
        self._set_params(create_vendor_bills=True)
        invoice = self._create_invoice(self.external_partner)
        invoice.action_post()
        self.assertFalse(self._bills(invoice.name))

    def test_existing_bill_is_not_duplicated(self):
        self._set_params(create_vendor_bills=True)
        invoice = self._create_invoice(self.partner_b)
        invoice.action_post()
        invoice.button_draft()
        invoice.action_post()
        self.assertEqual(len(self._bills(invoice.name)), 1)

    def test_restricted_product_raises(self):
        self._set_params(create_vendor_bills=True)
        product = self.env['product.product'].create({
            'name': 'Company A Only',
            'company_id': self.company_a.id,
        })
        invoice = self._create_invoice(self.partner_b, product=product)
        with self.assertRaises(UserError):
            invoice.action_post()

    def test_non_customer_invoice_is_ignored(self):
        self._set_params(create_vendor_bills=True)
        refund = self._create_invoice(self.partner_b)
        refund.move_type = 'out_refund'
        refund.action_post()
        self.assertFalse(self._bills(refund.name))

    def test_sale_order_invoice_creates_bill_from_purchase_order(self):
        self._set_params(
            create_vendor_bills=True,
            create_purchase_orders=True,
            create_sale_orders=True,
        )
        so = self._create_so(self.partner_b, qty=3)
        so.action_confirm()
        po = so.intercompany_purchase_order_id
        po.with_company(self.company_b).button_confirm()
        # Receive goods in company B so the PO becomes invoiceable.
        receipt = po.picking_ids.filtered(
            lambda p: p.picking_type_code == 'incoming')
        receipt.move_ids.write({'quantity': 3, 'picked': True})
        receipt.with_context(skip_backorder=True).button_validate()
        so.order_line.qty_delivered = 3
        invoice = so._create_invoices()
        invoice.action_post()
        self.assertEqual(len(self._bills(po.name)), 1)

    def test_sale_order_invoice_without_receipt_logs_message(self):
        self._set_params(
            create_vendor_bills=True,
            create_purchase_orders=True,
        )
        so = self._create_so(self.partner_b, qty=3)
        so.action_confirm()
        po = so.intercompany_purchase_order_id
        po.with_company(self.company_b).button_confirm()
        so.order_line.qty_delivered = 3
        invoice = so._create_invoices()
        invoice.action_post()
        self.assertFalse(self._bills(po.name))
        self.assertTrue(any(
            'nothing to invoice' in (m.body or '') for m in po.message_ids))
