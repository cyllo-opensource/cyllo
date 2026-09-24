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
from odoo.tests import common
from odoo.exceptions import UserError


class TestSubscriptionOrderLine(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.partner = cls.env['res.partner'].create({'name': 'Test Partner'})
        cls.product = cls.env['product.product'].create({'name': 'Test Product'})
        cls.tax = cls.env['account.tax'].create({
            'name': 'Test Tax',
            'amount': 10,
            'type_tax_use': 'sale'
        })

        cls.subscription_order = cls.env['subscription.order'].create({
            'name': 'Test Subscription Order',
            'partner_id': cls.partner.id,
            'state': 'draft'
        })

        cls.subscription_order_line_draft = cls.env['subscription.order.line'].create({
            'product_id': cls.product.id,
            'quantity': 1,
            'subtotal': 100.0,
            'total_price': 110.0,
            'tax_ids': [(4, cls.tax.id)],
            'subscription_order_id': cls.subscription_order.id,
            'state': 'draft'
        })

        cls.subscription_order_line_confirmed = cls.env['subscription.order.line'].create({
            'product_id': cls.product.id,
            'quantity': 2,
            'subtotal': 200.0,
            'total_price': 220.0,
            'tax_ids': [(4, cls.tax.id)],
            'subscription_order_id': cls.subscription_order.id,
            'state': 'sale'
        })

    def test_unlink_except_confirmed(self):
        self.subscription_order_line_draft.unlink()
        remaining_lines = self.env['subscription.order.line'].search([
            ('id', '=', self.subscription_order_line_draft.id)
        ])
        self.assertFalse(remaining_lines, "Draft lines should be deletable.")
        with self.assertRaises(UserError, msg="A confirmed line should raise a UserError on deletion."):
            self.subscription_order_line_confirmed.unlink()

    def test_check_line_unlink(self):
        """Test the _check_line_unlink helper method."""
        unlinkable_lines = self.subscription_order_line_confirmed._check_line_unlink()
        self.assertIn(self.subscription_order_line_confirmed, unlinkable_lines,
                      "Confirmed lines should be included in the unlinkable lines.")
        self.assertNotIn(self.subscription_order_line_draft, unlinkable_lines,
                         "Draft lines should not be included in the unlinkable lines.")
