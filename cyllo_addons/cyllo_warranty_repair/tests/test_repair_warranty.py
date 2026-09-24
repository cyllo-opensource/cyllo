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
from odoo import fields


@tagged('post_install', '-at_install')
class TestRepairWarranty(TransactionCase):
    """Tests for Warranty Repair module: repair orders and sale integration."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Create partners/customers
        cls.customer = cls.env['res.partner'].create({
            'name': 'Test Customer',
            'email': 'customer@test.com',
        })

        cls.other_customer = cls.env['res.partner'].create({
            'name': 'Other Customer',
            'email': 'other@test.com',
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

    def test_repair_order_compute_warranty_status(self):
        """Test the compute method for warranty_status on Repair Order."""
        # 1. No sale order line set
        repair = self.env['repair.order'].create({
            'product_id': self.product_warranty.id,
            'partner_id': self.customer.id,
        })
        self.assertFalse(repair.warranty_status)

        # Create a Sale Order and Lines
        so = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'date_order': self.today,
        })

        # Line with future expiration (12 months from today)
        so_line_warranty = self.env['sale.order.line'].create({
            'order_id': so.id,
            'product_id': self.product_warranty.id,
            'product_uom_qty': 1,
        })

        # Line with no expiration (category has no warranty)
        so_line_no_warranty = self.env['sale.order.line'].create({
            'order_id': so.id,
            'product_id': self.product_no_warranty.id,
            'product_uom_qty': 1,
        })

        # 2. Under Warranty status
        repair.write({
            'sale_order_line_id': so_line_warranty.id,
        })
        repair._compute_warranty_status()
        self.assertEqual(repair.warranty_status, 'under_warranty')

        # 3. No Warranty status
        repair.write({
            'sale_order_line_id': so_line_no_warranty.id,
        })
        repair._compute_warranty_status()
        self.assertEqual(repair.warranty_status, 'none')

        # 4. Expired status (simulate past date order so expiration is in the past)
        past_so = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'date_order': self.today - timedelta(days=500),
        })
        so_line_expired = self.env['sale.order.line'].create({
            'order_id': past_so.id,
            'product_id': self.product_warranty.id,
            'product_uom_qty': 1,
        })

        repair.write({
            'sale_order_line_id': so_line_expired.id,
        })
        repair._compute_warranty_status()
        self.assertEqual(repair.warranty_status, 'expired')

    def test_repair_order_onchange_sale_order_id(self):
        """Test onchange_sale_order_id behavior on Repair Order."""
        # Create Sale Order for customer
        so = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'date_order': self.today,
        })

        so_line = self.env['sale.order.line'].create({
            'order_id': so.id,
            'product_id': self.product_warranty.id,
            'product_uom_qty': 1,
        })

        repair = self.env['repair.order'].new({
            'product_id': self.product_warranty.id,
            'partner_id': self.other_customer.id, # different customer initially
        })

        # Change sale order
        repair.sale_order_id = so
        repair._onchange_sale_order_id()

        # Partner should update to match sale order's partner
        self.assertEqual(repair.partner_id, self.customer)

        # Set a sale order line from this sale order
        repair.sale_order_line_id = so_line

        # Create another Sale Order for other_customer
        other_so = self.env['sale.order'].create({
            'partner_id': self.other_customer.id,
            'date_order': self.today,
        })

        # Change to other_so
        repair.sale_order_id = other_so
        repair._onchange_sale_order_id()

        # Since so_line belongs to so, it should be cleared
        self.assertFalse(repair.sale_order_line_id)

        # Set sale_order_id to False
        repair.sale_order_id = False
        repair._onchange_sale_order_id()
        self.assertFalse(repair.sale_order_line_id)

    def test_repair_order_onchange_sale_order_line_id(self):
        """Test onchange_sale_order_line_id behavior on Repair Order."""
        so = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'date_order': self.today,
        })

        # Line with warranty
        so_line_warranty = self.env['sale.order.line'].create({
            'order_id': so.id,
            'product_id': self.product_warranty.id,
            'product_uom_qty': 1,
        })

        # Line with no warranty
        so_line_no_warranty = self.env['sale.order.line'].create({
            'order_id': so.id,
            'product_id': self.product_no_warranty.id,
            'product_uom_qty': 1,
        })

        repair = self.env['repair.order'].new({
            'partner_id': self.customer.id,
        })

        # 1. Select warranty line (future expiration date)
        repair.sale_order_line_id = so_line_warranty
        repair._onchange_sale_order_line_id()

        self.assertEqual(repair.product_id, self.product_warranty)
        self.assertEqual(repair.warranty_status, 'under_warranty')
        self.assertTrue(repair.under_warranty)

        # 2. Select no warranty line
        repair.sale_order_line_id = so_line_no_warranty
        repair._onchange_sale_order_line_id()

        self.assertEqual(repair.product_id, self.product_no_warranty)
        self.assertEqual(repair.warranty_status, 'none')
        self.assertFalse(repair.under_warranty)

        # 3. Select expired line (simulate past date order)
        past_so = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'date_order': self.today - timedelta(days=500),
        })
        so_line_expired = self.env['sale.order.line'].create({
            'order_id': past_so.id,
            'product_id': self.product_warranty.id,
            'product_uom_qty': 1,
        })

        repair.sale_order_line_id = so_line_expired
        repair._onchange_sale_order_line_id()

        self.assertEqual(repair.product_id, self.product_warranty)
        self.assertEqual(repair.warranty_status, 'expired')
        self.assertFalse(repair.under_warranty)
