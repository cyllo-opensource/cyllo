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
class TestSaleWarranty(TransactionCase):
    """Tests for Warranty Sale module: sale orders, lines, stock moves, and wizard."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Create partner/customer
        cls.customer = cls.env['res.partner'].create({
            'name': 'Test Customer',
            'email': 'customer@test.com',
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

    def test_sale_order_line_warranty_expiration_date(self):
        """Test calculation of warranty expiration date on sale order lines."""
        so = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'date_order': self.today,
        })

        so_line_warranty = self.env['sale.order.line'].create({
            'order_id': so.id,
            'product_id': self.product_warranty.id,
            'product_uom_qty': 1,
            'price_unit': 100.0,
        })

        so_line_no_warranty = self.env['sale.order.line'].create({
            'order_id': so.id,
            'product_id': self.product_no_warranty.id,
            'product_uom_qty': 1,
            'price_unit': 50.0,
        })

        # Base expiration date check
        expected_exp = self.product_warranty._get_warranty_expiration_date(self.today)
        self.assertEqual(so_line_warranty.sale_warranty_expiration_date, expected_exp)
        self.assertFalse(so_line_no_warranty.sale_warranty_expiration_date)

    def test_sale_order_line_warranty_extension(self):
        """Test how manual extension values affect expiration date."""
        so = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'date_order': self.today,
        })

        so_line = self.env['sale.order.line'].create({
            'order_id': so.id,
            'product_id': self.product_warranty.id,
            'product_uom_qty': 1,
            'price_unit': 100.0,
            'warranty_extension_period': 6,
            'warranty_extension_unit': 'month',
        })

        # Base warranty is 12 months + 6 months extension = 18 months
        base_exp = self.product_warranty._get_warranty_expiration_date(self.today)
        from dateutil.relativedelta import relativedelta
        correct_calculation = base_exp + relativedelta(months=6)
        self.assertEqual(so_line.sale_warranty_expiration_date, correct_calculation)

        # Test year extension unit
        so_line.write({
            'warranty_extension_period': 2,
            'warranty_extension_unit': 'year',
        })
        self.assertEqual(so_line.sale_warranty_expiration_date, base_exp + relativedelta(years=2))

        # Test day extension unit
        so_line.write({
            'warranty_extension_period': 15,
            'warranty_extension_unit': 'day',
        })
        self.assertEqual(so_line.sale_warranty_expiration_date, base_exp + relativedelta(days=15))

    def test_sale_order_line_is_under_warranty_and_search(self):
        """Test calculation of is_under_warranty and the custom search method."""
        so = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'date_order': self.today,
        })

        so_line = self.env['sale.order.line'].create({
            'order_id': so.id,
            'product_id': self.product_warranty.id,
            'product_uom_qty': 1,
        })

        self.assertTrue(so_line.is_under_warranty)

        # Move date back to trigger expired status
        past_date = self.today - timedelta(days=500)
        so.write({
            'date_order': past_date,
        })
        so_line._compute_sale_warranty_expiration_date()
        so_line._compute_is_under_warranty()
        self.assertFalse(so_line.is_under_warranty)

        # Test search method
        lines_under_warranty = self.env['sale.order.line'].search([
            ('id', '=', so_line.id),
            ('is_under_warranty', '=', True),
        ])
        self.assertNotIn(so_line, lines_under_warranty)

        lines_not_under_warranty = self.env['sale.order.line'].search([
            ('id', '=', so_line.id),
            ('is_under_warranty', '=', False),
        ])
        self.assertIn(so_line, lines_not_under_warranty)

    def test_sale_order_display_extend_warranty(self):
        """Test display_extend_warranty compute field."""
        # Deactivate config parameter
        self.env['ir.config_parameter'].sudo().set_param(
            'cyllo_product_warranty.is_extend_warranty', False
        )

        so = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'date_order': self.today,
        })

        so_line = self.env['sale.order.line'].create({
            'order_id': so.id,
            'product_id': self.product_warranty.id,
            'product_uom_qty': 1,
        })

        so._compute_display_extend_warranty()
        self.assertFalse(so.display_extend_warranty)

        # Activate config parameter
        self.env['ir.config_parameter'].sudo().set_param(
            'cyllo_product_warranty.is_extend_warranty', True
        )
        so._compute_display_extend_warranty()
        self.assertTrue(so.display_extend_warranty)

    def test_sale_order_action_extend_warranty_and_wizard(self):
        """Test the action to extend warranty and the wizard logic."""
        so_no_war = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'date_order': self.today,
        })
        self.env['sale.order.line'].create({
            'order_id': so_no_war.id,
            'product_id': self.product_no_warranty.id,
            'product_uom_qty': 1,
        })

        # Should raise error if no warranty product
        with self.assertRaises(UserError):
            so_no_war.action_extend_warranty()

        # Should return action if warranty product is present
        so_war = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'date_order': self.today,
        })
        so_line = self.env['sale.order.line'].create({
            'order_id': so_war.id,
            'product_id': self.product_warranty.id,
            'product_uom_qty': 1,
        })

        action = so_war.action_extend_warranty()
        self.assertEqual(action.get('res_model'), 'warranty.extension.wizard')

        # Test wizard confirm
        wizard = self.env['warranty.extension.wizard'].with_context(
            action.get('context')
        ).create({
            'order_id': so_war.id,
            'line_ids': [(6, 0, [so_line.id])],
            'extension_period': 3,
            'extension_unit': 'month',
        })

        initial_extension = so_line.warranty_extension_period
        wizard.action_confirm()

        self.assertEqual(so_line.warranty_extension_period, initial_extension + 3)
        self.assertEqual(so_line.warranty_extension_unit, 'month')

    def test_stock_move_line_warranty_propagation(self):
        """Test that the warranty expiration date propagates to stock.move.line."""
        so = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'date_order': self.today,
        })

        so_line = self.env['sale.order.line'].create({
            'order_id': so.id,
            'product_id': self.product_warranty.id,
            'product_uom_qty': 1,
            'price_unit': 100.0,
        })

        # Confirm the Sale Order to generate warehouse picking / delivery order
        so.action_confirm()

        picking = so.picking_ids
        self.assertTrue(picking)

        move = picking.move_ids.filtered(lambda m: m.sale_line_id == so_line)
        self.assertTrue(move)

        # Create stock.move.line to verify the compute method
        move_line = self.env['stock.move.line'].create({
            'move_id': move.id,
            'product_id': self.product_warranty.id,
            'product_uom_id': self.product_warranty.uom_id.id,
            'location_id': move.location_id.id,
            'location_dest_id': move.location_dest_id.id,
            'quantity': 1.0,
        })

        move_line._compute_sale_warranty_expiration_date()
        self.assertEqual(move_line.sale_warranty_expiration_date, so_line.sale_warranty_expiration_date)
