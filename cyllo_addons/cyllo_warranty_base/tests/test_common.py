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

from odoo.tests import TransactionCase


class WarrantyBaseTestCommon(TransactionCase):
    """Common test setup for Warranty Base module tests."""

    @classmethod
    def setUpClass(cls):
        """Set up test data shared across all warranty base test cases."""
        super().setUpClass()

        # Create a product category with warranty settings
        cls.category_warranty = cls.env['product.category'].create({
            'name': 'Category With Warranty',
            'warranty_period': 12,
            'warranty_period_unit': 'month',
        })

        # Create a product category without warranty
        cls.category_no_warranty = cls.env['product.category'].create({
            'name': 'Category No Warranty',
            'warranty_period': 0,
            'warranty_period_unit': 'month',
        })

        # Create a product template with its own warranty (overrides category)
        cls.product_template_warranty = cls.env['product.template'].create({
            'name': 'Product With Own Warranty',
            'type': 'consu',
            'list_price': 500.0,
            'categ_id': cls.category_warranty.id,
            'warranty_period': 24,
            'warranty_period_unit': 'month',
        })

        # Create a product template that relies on category warranty
        cls.product_template_category_warranty = cls.env['product.template'].create({
            'name': 'Product With Category Warranty',
            'type': 'consu',
            'list_price': 200.0,
            'categ_id': cls.category_warranty.id,
            'warranty_period': 0,
            'warranty_period_unit': 'month',
        })

        # Create a product template with no warranty at all
        cls.product_template_no_warranty = cls.env['product.template'].create({
            'name': 'Product No Warranty',
            'type': 'consu',
            'list_price': 50.0,
            'categ_id': cls.category_no_warranty.id,
            'warranty_period': 0,
            'warranty_period_unit': 'month',
        })

        # Get the product.product variants
        cls.product_own_warranty = cls.product_template_warranty.product_variant_id
        cls.product_category_warranty = cls.product_template_category_warranty.product_variant_id
        cls.product_no_warranty = cls.product_template_no_warranty.product_variant_id
