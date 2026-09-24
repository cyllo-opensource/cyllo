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


class TestSaleOrder(TransactionCase):
    """
    Test suite for verifying the functionality of the `action_merge_quotation`
    method in the Sale Order model.

    This test ensures:
        * Validation errors are correctly raised for invalid merge scenarios.
        * Quotations are properly merged when valid conditions are met.
        * Merged order lines consolidate quantities based on product and price.
        * Resulting actions and redirections are correctly returned.
    """
    @classmethod
    def setUpClass(cls):
        """
        Test data setup executed once for the entire test class.

        Creates:
            - Two partner records (partner_a, partner_b).
            - Two product records (product_a, product_b).
            - Initializes environment variables for sale orders and related models.
        """
        super(TestSaleOrder, cls).setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.SaleOrder = cls.env['sale.order']
        cls.Partner = cls.env['res.partner']
        cls.Product = cls.env['product.product']
        cls.partner_a = cls.Partner.create({'name': 'Test Partner A'})
        cls.partner_b = cls.Partner.create({'name': 'Test Partner B'})
        cls.product_a = cls.Product.create({
            'name': 'Test Product A',
            'type': 'service',
            'list_price': 100.0,
        })
        cls.product_b = cls.Product.create({
            'name': 'Test Product B',
            'type': 'service',
            'list_price': 50.0,
        })

    def test_action_merge_quotation(self):
        """
        Validate the `action_merge_quotation` behavior across multiple scenarios:

        Test Cases Covered:
            1. Single quotation merge attempt → Raises ValidationError.
            2. Merging quotations with different partners → Raises ValidationError.
            3. Merging quotations where one is not in draft → Raises ValidationError.
            4. Valid merge of quotations with same partner and draft state:
               - Consolidates order lines correctly.
               - Deletes original quotations.
               - Returns valid ir.actions.act_window redirect.
        """
        order1 = self.SaleOrder.create({'partner_id': self.partner_a.id})
        with self.assertRaisesRegex(
                ValidationError,
                "Please select at least two orders to merge."
        ):
            order1.action_merge_quotation()
        order1 = self.SaleOrder.create({'partner_id': self.partner_a.id})
        order2 = self.SaleOrder.create({'partner_id': self.partner_b.id})
        orders_to_merge = order1 | order2
        with self.assertRaisesRegex(
                ValidationError,
                "Selected orders have different partners."
        ):
            orders_to_merge.action_merge_quotation()
        order3 = self.SaleOrder.create({'partner_id': self.partner_a.id})
        order4 = self.SaleOrder.create({'partner_id': self.partner_a.id})
        order3.action_confirm()
        self.assertEqual(order3.state, 'sale')
        order_merges = order3 | order4
        with self.assertRaisesRegex(
                ValidationError,
                "Please select orders in the quotation state."
        ):
            order_merges.action_merge_quotation()
        order1 = self.SaleOrder.create({
            'partner_id': self.partner_a.id,
            'order_line': [
                (0, 0, {'product_id': self.product_a.id, 'product_uom_qty': 10,
                        'price_unit': 100.0}),
                (0, 0, {'product_id': self.product_b.id, 'product_uom_qty': 5,
                        'price_unit': 50.0}),
            ]
        })
        order2 = self.SaleOrder.create({
            'partner_id': self.partner_a.id,
            'order_line': [
                (0, 0, {'product_id': self.product_a.id, 'product_uom_qty': 7,
                        'price_unit': 100.0}),
                (0, 0, {'product_id': self.product_a.id, 'product_uom_qty': 3,
                        'price_unit': 110.0}),
            ]
        })
        order1_id = order1.id
        order2_id = order2.id
        orders_to_merge = order1 | order2
        original_order_count = self.SaleOrder.search_count([])
        action = orders_to_merge.action_merge_quotation()
        self.assertEqual(self.SaleOrder.search_count([]), original_order_count - 1)
        self.assertFalse(self.SaleOrder.browse(order1_id).exists())
        self.assertFalse(self.SaleOrder.browse(order2_id).exists())
        new_order_id = action.get('res_id')
        self.assertTrue(new_order_id)
        new_order = self.SaleOrder.browse(action['res_id'])
        self.assertEqual(new_order.partner_id, self.partner_a)
        self.assertEqual(len(new_order.order_line), 3)
        line_a_100 = new_order.order_line.filtered(
            lambda l: l.product_id == self.product_a and l.price_unit == 100.0
        )
        self.assertEqual(line_a_100.product_uom_qty, 17)
        line_b_50 = new_order.order_line.filtered(
            lambda l: l.product_id == self.product_b and l.price_unit == 50.0
        )
        self.assertEqual(line_b_50.product_uom_qty, 5)
        line_a_110 = new_order.order_line.filtered(
            lambda l: l.product_id == self.product_a and l.price_unit == 110.0
        )
        self.assertEqual(line_a_110.product_uom_qty, 3)
        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(action['res_model'],'sale.order')
        self.assertEqual(action['view_mode'], 'form')
        self.assertEqual(action['target'], 'current')
        self.assertEqual(action['res_id'], new_order_id)
