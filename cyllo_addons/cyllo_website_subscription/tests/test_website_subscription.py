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
from odoo.tests import common, tagged


@tagged('post_install', '-at_install')
class TestWebsiteSubscriptionCart(common.TransactionCase):
    """Tests for the e-commerce behaviour of subscription orders."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.website = cls.env['website'].get_current_website()
        cls.partner = cls.env['res.partner'].create({
            'name': 'Subscription Shopper',
        })
        cls.trial_product = cls.env.ref(
            'cyllo_subscription.product_trial_discount',
            raise_if_not_found=False,
        )
        cls.product = cls.env['product.product'].create({
            'name': 'Website Widget',
            'list_price': 100.0,
            'website_published': True,
        })

    def _create_order(self):
        return self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'website_id': self.website.id,
        })

    def test_trial_discount_product_is_shipped(self):
        """The subscription module provides the trial discount product."""
        self.assertTrue(
            self.trial_product,
            "cyllo_subscription.product_trial_discount should exist",
        )

    def test_regular_line_is_shown_in_cart(self):
        """An ordinary product line stays visible in the cart."""
        order = self._create_order()
        line = self.env['sale.order.line'].create({
            'order_id': order.id,
            'product_id': self.product.id,
            'product_uom_qty': 1,
        })
        self.assertTrue(line._show_in_cart())

    def test_trial_discount_line_is_hidden_from_cart(self):
        """The generated trial discount line is not displayed in the cart."""
        if not self.trial_product:
            self.skipTest("Trial discount product is not available")
        order = self._create_order()
        line = self.env['sale.order.line'].create({
            'order_id': order.id,
            'product_id': self.trial_product.id,
            'product_uom_qty': 1,
            'price_unit': -50.0,
        })
        self.assertFalse(line._show_in_cart())

    def test_trial_offset_without_discount_lines(self):
        """An order without trial lines reports a zero offset."""
        order = self._create_order()
        total, tax, subtotal = order._get_subscription_trial_offset()
        self.assertEqual((total, tax, subtotal), (0.0, 0.0, 0.0))

    def test_trial_offset_reads_the_discount_lines(self):
        """The offset is the absolute value of the trial discount lines."""
        if not self.trial_product:
            self.skipTest("Trial discount product is not available")
        order = self._create_order()
        self.env['sale.order.line'].create({
            'order_id': order.id,
            'product_id': self.trial_product.id,
            'product_uom_qty': 1,
            'price_unit': -75.0,
            'tax_id': [(5, 0, 0)],
        })
        total, tax, subtotal = order._get_subscription_trial_offset()
        self.assertAlmostEqual(subtotal, 75.0, places=2)
        self.assertAlmostEqual(total, 75.0, places=2)

    def test_cart_line_lookup_ignores_plan_less_lines(self):
        """Looking up a cart line without a plan skips lines that have one."""
        order = self._create_order()
        line = self.env['sale.order.line'].create({
            'order_id': order.id,
            'product_id': self.product.id,
            'product_uom_qty': 1,
        })
        found = order._cart_find_product_line(self.product.id)
        self.assertIn(line, found)


@tagged('post_install', '-at_install')
class TestWebsiteSubscriptionOverrides(common.TransactionCase):
    """Tests that the website subscription overrides are wired in."""

    def test_product_template_override_is_installed(self):
        """product.template exposes the subscription aware combination info."""
        self.assertTrue(hasattr(self.env['product.template'],
                                '_get_combination_info'))
        self.assertTrue(hasattr(self.env['product.template'],
                                '_search_render_results'))

    def test_sale_order_override_is_installed(self):
        """sale.order exposes the trial discount helpers."""
        order_model = self.env['sale.order']
        self.assertTrue(hasattr(order_model, '_set_trial_discount_line'))
        self.assertTrue(hasattr(order_model, '_get_subscription_trial_offset'))

    def test_combination_info_without_plan_is_unchanged(self):
        """A plain product keeps the standard combination info."""
        template = self.env['product.template'].create({
            'name': 'Plain Website Product',
            'list_price': 25.0,
            'website_published': True,
        })
        info = template._get_combination_info()
        self.assertEqual(info['product_template_id'], template.id)
        self.assertNotIn('sub_pricing_id', info)
