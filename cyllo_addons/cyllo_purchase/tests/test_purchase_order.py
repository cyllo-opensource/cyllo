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
from odoo.exceptions import ValidationError


class TestPurchaseOrderMerge(TransactionCase):
    """Simple test case for Purchase Order RFQ merge."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.PurchaseOrder = cls.env['purchase.order']
        cls.Partner = cls.env['res.partner']
        cls.Product = cls.env['product.product']

        cls.partner = cls.Partner.create({'name': 'Vendor A'})
        cls.product_a = cls.Product.create({'name': 'Product A', 'type': 'service', 'standard_price': 100})
        cls.product_b = cls.Product.create({'name': 'Product B', 'type': 'service', 'standard_price': 50})
        cls.order = cls.PurchaseOrder.create({
            'partner_id': cls.partner.id,
            'order_line': [
                (0, 0, {
                    'name': cls.product_a.name,
                    'product_id': cls.product_a.id,
                    'product_qty': 2,
                    'price_unit': 100,
                }),
                (0, 0, {
                    'name': cls.product_b.name,
                    'product_id': cls.product_b.id,
                    'product_qty': 1,
                    'price_unit': 200,
                }),
            ]
        })

    def test_action_merge_rfq(self):
        """Test merging multiple RFQs for the same vendor."""
        rfq1 = self.PurchaseOrder.create({'partner_id': self.partner.id})
        with self.assertRaises(ValidationError):
            rfq1.action_merge_rfq()

        vendor_b = self.Partner.create({'name': 'Vendor B'})
        rfq1 = self.PurchaseOrder.create({'partner_id': self.partner.id})
        rfq2 = self.PurchaseOrder.create({'partner_id': vendor_b.id})
        with self.assertRaises(ValidationError):
            (rfq1 | rfq2).action_merge_rfq()

        rfq3 = self.PurchaseOrder.create({'partner_id': self.partner.id})
        rfq4 = self.PurchaseOrder.create({'partner_id': self.partner.id})
        rfq3.write({'state': 'purchase'})
        with self.assertRaises(ValidationError):
            (rfq3 | rfq4).action_merge_rfq()

        rfq1 = self.PurchaseOrder.create({
            'partner_id': self.partner.id,
            'order_line': [
                (0, 0, {'product_id': self.product_a.id, 'product_qty': 5, 'price_unit': 100}),
                (0, 0, {'product_id': self.product_b.id, 'product_qty': 10, 'price_unit': 50}),
            ]
        })
        rfq2 = self.PurchaseOrder.create({
            'partner_id': self.partner.id,
            'order_line': [
                (0, 0, {'product_id': self.product_a.id, 'product_qty': 7, 'price_unit': 100}),
                (0, 0, {'product_id': self.product_a.id, 'product_qty': 3, 'price_unit': 110}),
            ]
        })

        merged_action = (rfq1 | rfq2).action_merge_rfq()
        self.assertIsInstance(merged_action, dict)
        self.assertEqual(merged_action.get('type'), 'ir.actions.act_window')
        self.assertEqual(merged_action.get('res_model'), 'purchase.order')
        self.assertEqual(merged_action.get('view_mode'), 'form')
        self.assertEqual(merged_action.get('target'), 'current')
        self.assertTrue(merged_action.get('res_id'))
        new_rfq = self.env['purchase.order'].browse(merged_action['res_id'])
        self.assertEqual(new_rfq.partner_id, self.partner)
        self.assertEqual(len(new_rfq.order_line), 3)
        qty_100 = new_rfq.order_line.filtered(lambda l: l.price_unit == 100).product_qty
        qty_50 = new_rfq.order_line.filtered(lambda l: l.price_unit == 50).product_qty
        qty_110 = new_rfq.order_line.filtered(lambda l: l.price_unit == 110).product_qty
        self.assertEqual(qty_100, 12)
        self.assertEqual(qty_50, 10)
        self.assertEqual(qty_110, 3)

    def test_action_apply_discount(self):
        """
        Verify discount logic for:
        1. Percentage discount.
        2. Fixed amount discount (proportional).
        3. Zero discount fallback.
        """
        self.order.write({
            'discount_type': 'percentage',
            'discount_percentage': 10,
        })
        self.order.action_apply_discount()
        for line in self.order.order_line:
            self.assertEqual(line.discount, 10.0)
        self.order.order_line.update({'discount': 0})
        self.order.write({
            'discount_type': 'amount',
            'discount_amount': 60,
        })
        self.order.action_apply_discount()
        for line in self.order.order_line:
            self.assertAlmostEqual(line.discount, 15.0, 2)
        self.order.order_line.update({'discount': 5})
        self.order.write({
            'discount_type': 'amount',
            'discount_amount': 0,
        })
        self.order.action_apply_discount()
        for line in self.order.order_line:
            self.assertEqual(line.discount, 0.0)
