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
from odoo.tests import TransactionCase


class TestSaleOrderDiscount(TransactionCase):
    """
    Test suite for validating the custom discount logic added to the
    'sale.order.discount' transient model.

    This class verifies that discounts are correctly applied either
    to order lines directly or via the inherited (super) method when
    'apply_order_lines' is False.
    """

    def setUp(self):
        """
        Setup test data before each test case execution.

        Creates:
            - A test partner.
            - A sale order with two order lines priced at 100 and 200 respectively.
        Ensures that the initial order total is 300.0.
        """
        super().setUp()
        self.partner = self.env['res.partner'].create({'name': 'Test Partner'})

        self.order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [
                (0, 0, {
                    'name': 'Product A',
                    'product_id': self.env.ref('product.product_product_1').id,
                    'product_uom_qty': 1,
                    'price_unit': 100,
                }),
                (0, 0, {
                    'name': 'Product B',
                    'product_id': self.env.ref('product.product_product_2').id,
                    'product_uom_qty': 1,
                    'price_unit': 200,
                }),
            ]
        })
        self.assertEqual(self.order.amount_total, 300)
    def test_create_discount_lines(self):
        """
        Test the '_create_discount_lines' method under different configurations.

        Covers:
            1. Applying percentage-based discount directly to order lines.
            2. Applying amount-based discount distributed across order lines.
            3. Fallback to the inherited super method when 'apply_order_lines' is False.

        Assertions:
            - Correct discount percentages applied per line.
            - Correct recalculation of total amounts after discount.
            - Super method creates a new discount line instead of modifying existing ones.
        """
        wizard_percentage = self.env['sale.order.discount'].create({
            'sale_order_id': self.order.id,
            'discount_type': 'so_discount',
            'discount_percentage': 0.10,  # 10%
            'apply_order_lines': True,
        })
        wizard_percentage._create_discount_lines()
        for line in self.order.order_line:
            self.assertEqual(line.discount, 10.0)
        self.assertAlmostEqual(self.order.amount_total, 270.0)
        for line in self.order.order_line:
            line.discount = 0
        self.assertAlmostEqual(self.order.amount_total, 300.0)
        expected_discount_percent = 30 * 100 / self.order.amount_total
        wizard_amount = self.env['sale.order.discount'].create({
            'sale_order_id': self.order.id,
            'discount_type': 'amount',
            'discount_amount': 30,  # fixed 30 off on total
            'apply_order_lines': True,
        })
        wizard_amount._create_discount_lines()
        for line in self.order.order_line:
            self.assertAlmostEqual(
                line.discount, expected_discount_percent, 2)
        self.assertAlmostEqual(self.order.amount_total, 270.0)
        for line in self.order.order_line:
            line.discount = 0
        self.assertAlmostEqual(self.order.amount_total, 300.0)
        wizard_super = self.env['sale.order.discount'].create({
            'sale_order_id': self.order.id,
            'discount_type': 'so_discount',
            'discount_percentage': 0.05,  # 5%
            'apply_order_lines': False,
        })
        prev_line_count = len(self.order.order_line)
        self.assertEqual(prev_line_count, 2)
        result = wizard_super._create_discount_lines()
        self.assertTrue(result)
        self.assertEqual(len(self.order.order_line), 3)
        self.assertEqual(self.order.order_line[0].discount, 0)
        self.assertEqual(self.order.order_line[1].discount, 0)
        self.assertAlmostEqual(self.order.amount_total, 285.0)
