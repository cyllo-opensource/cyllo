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
from odoo.tests.common import TransactionCase


class TestSaleOrderLine(TransactionCase):
    """

    """
    @classmethod
    def setUp(cls):
        super().setUpClass()

        cls.partner = cls.env['res.partner'].create({'name': 'Partner'})
        cls.product = cls.env['product.product'].create({
            'name': 'Product A',
            'list_price': 50.00
        })
        cls.sale_order = cls.env['sale.order'].create({
            'partner_id': cls.partner.id,
            'order_line': [(0, 0, {
                'product_id': cls.product.id,
                'product_uom_qty': 2.0,
                'product_uom': cls.product.uom_id.id,
                'price_unit': 100.00,
            })]
        })
        cls.sale_order.action_confirm()
        cls.sale_order_line = cls.sale_order.order_line[0]

    def test_compute_price_subtotal_latest(self):
        """

        """
        self.sale_order_line._compute_price_subtotal_latest()
        self.assertEqual(
            self.sale_order_line.price_subtotal_latest,
            self.sale_order_line.price_subtotal)

        invoice = self.sale_order._create_invoices()
        invoice.action_post()
        refund = invoice.copy({
            'move_type': 'out_refund',
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product.id,
                'quantity': 1.0,
                'price_unit': 50.00,
            })]
        })
        refund.action_post()
        refund.write({'payment_state': 'partial'})

        self.sale_order_line._compute_price_subtotal_latest()
        expected = self.sale_order_line.price_subtotal - refund.invoice_line_ids[0].price_subtotal
        self.assertEqual(
            self.sale_order_line.price_subtotal_latest,
            expected)