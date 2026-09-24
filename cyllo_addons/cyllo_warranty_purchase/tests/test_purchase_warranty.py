# -*- coding: utf-8 -*-
#############################################################################
#
#    Cyllo Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cyllo(<https://www.cyllo.com>)
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

from datetime import date, timedelta
from odoo.tests import tagged, TransactionCase
from odoo.exceptions import UserError
from odoo import fields


@tagged('post_install', '-at_install')
class TestPurchaseWarranty(TransactionCase):
    """Tests for Warranty Purchase module: purchase orders, lines, stock moves, and wizard."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Create partner/vendor
        cls.vendor = cls.env['res.partner'].create({
            'name': 'Test Vendor',
            'email': 'vendor@test.com',
        })

        # Create product category with warranty
        cls.category_warranty = cls.env['product.category'].create({
            'name': 'Category with Warranty',
            'warranty_period': 12,
            'warranty_period_unit': 'month',
        })

        # Create product category without warranty
        cls.category_no_warranty = cls.env['product.category'].create({
            'name': 'Category no Warranty',
            'warranty_period': 0,
            'warranty_period_unit': 'month',
        })

        # Create products
        cls.product_warranty = cls.env['product.product'].create({
            'name': 'Product with Warranty',
            'type': 'product',
            'categ_id': cls.category_warranty.id,
        })

        cls.product_no_warranty = cls.env['product.product'].create({
            'name': 'Product no Warranty',
            'type': 'product',
            'categ_id': cls.category_no_warranty.id,
        })

    def setUp(self):
        super().setUp()
        self.today = fields.Date.today()

    def test_purchase_order_line_warranty_expiration_date(self):
        """Test calculation of warranty expiration date on purchase order lines."""
        # Create a PO with draft status
        po = self.env['purchase.order'].create({
            'partner_id': self.vendor.id,
            'date_order': self.today,
        })

        po_line_warranty = self.env['purchase.order.line'].create({
            'order_id': po.id,
            'product_id': self.product_warranty.id,
            'product_qty': 1,
            'price_unit': 100.0,
        })

        po_line_no_warranty = self.env['purchase.order.line'].create({
            'order_id': po.id,
            'product_id': self.product_no_warranty.id,
            'product_qty': 1,
            'price_unit': 50.0,
        })

        # When draft, expiration date is computed using date_order as date_approve is False
        self.assertFalse(po.date_approve)
        self.assertEqual(po_line_warranty.purchase_warranty_expiration_date, self.today + timedelta(days=365))  # approximate, 12 months later
        self.assertFalse(po_line_no_warranty.purchase_warranty_expiration_date)

        # Test date_approve is preferred when set
        approve_date = self.today - timedelta(days=10)
        po.write({
            'date_approve': approve_date,
            'state': 'purchase',
        })
        po_line_warranty._compute_purchase_warranty_expiration_date()
        
        expected_exp = self.product_warranty._get_warranty_expiration_date(approve_date)
        self.assertEqual(po_line_warranty.purchase_warranty_expiration_date, expected_exp)

    def test_purchase_order_line_warranty_extension(self):
        """Test how manual extension values affect expiration date."""
        po = self.env['purchase.order'].create({
            'partner_id': self.vendor.id,
            'date_order': self.today,
        })

        po_line = self.env['purchase.order.line'].create({
            'order_id': po.id,
            'product_id': self.product_warranty.id,
            'product_qty': 1,
            'price_unit': 100.0,
            'warranty_extension_days': 182, # ≈ 6 months
        })

        # Base warranty is 12 months (from category) + 6 months extension = 18 months
        base_exp = self.product_warranty._get_warranty_expiration_date(self.today)
        expected_exp = base_exp + timedelta(days=182)  # relativedelta adds 6 months, we assert correct computation
        
        # Verify it computed correctly
        from dateutil.relativedelta import relativedelta
        correct_calculation = base_exp + relativedelta(months=6)
        self.assertEqual(po_line.purchase_warranty_expiration_date, correct_calculation)

        # Test year extension unit
            'warranty_extension_days': 182 + 730, # add 2 years ≈ 730 days
        })
        self.assertEqual(po_line.purchase_warranty_expiration_date, base_exp + relativedelta(years=2))

        # Test day extension unit
            'warranty_extension_days': 182 + 730 + 15,
        })
        self.assertEqual(po_line.purchase_warranty_expiration_date, base_exp + relativedelta(days=15))

    def test_purchase_order_line_is_under_warranty_and_search(self):
        """Test calculation of is_under_warranty and the custom search method."""
        po = self.env['purchase.order'].create({
            'partner_id': self.vendor.id,
            'date_order': self.today,
        })

        po_line = self.env['purchase.order.line'].create({
            'order_id': po.id,
            'product_id': self.product_warranty.id,
            'product_qty': 1,
        })

        # Expiry is in 12 months, so it should be under warranty
        self.assertTrue(po_line.is_under_warranty)

        # Set expiration date in the past
            'warranty_extension_days': -395, # This should decrease/nullify/move it back (if allowed) or we can manipulate manually
        })
        # Wait, let's look at how _compute_warranty_expiration_date is defined:
        # If line.warranty_extension_days > 0: it adds. Let's force a past date_order / date_approve instead.
        past_date = self.today - timedelta(days=500)
        po.write({
            'date_approve': past_date,
            'state': 'purchase',
        })
        # Recalculate
        po_line._compute_purchase_warranty_expiration_date()
        po_line._compute_is_under_warranty()
        # 500 days ago + 12 months (~365 days) = expired about 135 days ago
        self.assertFalse(po_line.is_under_warranty)

        # Test search method
        lines_under_warranty = self.env['purchase.order.line'].search([
            ('id', '=', po_line.id),
            ('is_under_warranty', '=', True),
        ])
        self.assertNotIn(po_line, lines_under_warranty)

        lines_not_under_warranty = self.env['purchase.order.line'].search([
            ('id', '=', po_line.id),
            ('is_under_warranty', '=', False),
        ])
        self.assertIn(po_line, lines_not_under_warranty)

    def test_purchase_order_display_extend_warranty(self):
        """Test display_extend_warranty compute field."""
        # Deactivate config parameter
        self.env['ir.config_parameter'].sudo().set_param(
            'cyllo_product_warranty.is_extend_warranty_purchase', False
        )

        po = self.env['purchase.order'].create({
            'partner_id': self.vendor.id,
            'date_order': self.today,
        })

        po_line = self.env['purchase.order.line'].create({
            'order_id': po.id,
            'product_id': self.product_warranty.id,
            'product_qty': 1,
        })

        po._compute_display_extend_warranty()
        self.assertFalse(po.display_extend_warranty)

        # Activate config parameter
        self.env['ir.config_parameter'].sudo().set_param(
            'cyllo_product_warranty.is_extend_warranty_purchase', True
        )
        po._compute_display_extend_warranty()
        self.assertTrue(po.display_extend_warranty)

    def test_purchase_order_action_extend_warranty_and_wizard(self):
        """Test the action to extend warranty and the wizard logic."""
        po_no_war = self.env['purchase.order'].create({
            'partner_id': self.vendor.id,
            'date_order': self.today,
        })
        self.env['purchase.order.line'].create({
            'order_id': po_no_war.id,
            'product_id': self.product_no_warranty.id,
            'product_qty': 1,
        })

        # Should raise error if no warranty product
        with self.assertRaises(UserError):
            po_no_war.action_extend_warranty()

        # Should return action if warranty product is present
        po_war = self.env['purchase.order'].create({
            'partner_id': self.vendor.id,
            'date_order': self.today,
        })
        po_line = self.env['purchase.order.line'].create({
            'order_id': po_war.id,
            'product_id': self.product_warranty.id,
            'product_qty': 1,
        })

        action = po_war.action_extend_warranty()
        self.assertEqual(action.get('res_model'), 'warranty.extension.wizard')

        # Test wizard confirm
        wizard = self.env['warranty.extension.wizard'].with_context(
            action.get('context')
        ).create({
            'purchase_order_id': po_war.id,
            'purchase_line_ids': [(6, 0, [po_line.id])],
            'extension_period': 3,
            'extension_unit': 'month',
        })

        initial_extension = po_line.warranty_extension_days
        wizard.action_confirm()

        self.assertEqual(po_line.warranty_extension_days, initial_extension + 90)

    def test_stock_move_line_warranty_propagation(self):
        """Test that the warranty expiration date propagates to stock.move.line."""
        # Create a PO with a warranty product
        po = self.env['purchase.order'].create({
            'partner_id': self.vendor.id,
            'date_order': self.today,
        })

        po_line = self.env['purchase.order.line'].create({
            'order_id': po.id,
            'product_id': self.product_warranty.id,
            'product_qty': 1,
            'price_unit': 100.0,
        })

        # Confirm the PO to create a picking / receipt
        po.button_confirm()

        # Find the stock move and line associated with this PO line
        picking = po.picking_ids
        self.assertTrue(picking)
        
        move = picking.move_ids.filtered(lambda m: m.purchase_line_id == po_line)
        self.assertTrue(move)

        # In Odoo, stock.move.line records are created during picking preparation or validation
        # Let's ensure the move line has the correct purchase_warranty_expiration_date
        move_line = self.env['stock.move.line'].create({
            'move_id': move.id,
            'product_id': self.product_warranty.id,
            'product_uom_id': self.product_warranty.uom_id.id,
            'location_id': move.location_id.id,
            'location_dest_id': move.location_dest_id.id,
            'quantity': 1.0,
        })

        move_line._compute_purchase_warranty_expiration_date()
        self.assertEqual(move_line.purchase_warranty_expiration_date, po_line.purchase_warranty_expiration_date)
