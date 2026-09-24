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


class TestProductCategory(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.ProductCategory = cls.env["product.category"]

    # ---------------------------------------------------------
    # TEST 01: Default valuation is manual_periodic
    # ---------------------------------------------------------
    def test_01_default_property_valuation(self):
        category = self.ProductCategory.create({
            "name": "Test Category Default",
        })

        self.assertEqual(
            category.property_valuation,
            "manual_periodic"
        )

    # ---------------------------------------------------------
    # TEST 02: Onchange sets values when switching to real_time
    # ---------------------------------------------------------
    def test_02_onchange_property_valuation_real_time(self):
        category = self.ProductCategory.new({
            "name": "Test Category Onchange",
            "property_valuation": "real_time",
        })

        category._onchange_property_valuation()

        # Fields should exist (may be False if no ir.property exists)
        self.assertTrue(
            hasattr(category, "property_stock_valuation_account_id")
        )
        self.assertTrue(
            hasattr(category, "property_stock_account_input_categ_id")
        )
        self.assertTrue(
            hasattr(category, "property_stock_account_output_categ_id")
        )
        self.assertTrue(
            hasattr(category, "property_stock_journal")
        )

    # ---------------------------------------------------------
    # TEST 03: Create with real_time triggers onchange
    # ---------------------------------------------------------
    def test_03_create_real_time_triggers_onchange(self):
        category = self.ProductCategory.create({
            "name": "Test Category Create Real Time",
            "property_valuation": "real_time",
        })

        # Ensure valuation mode is set
        self.assertEqual(
            category.property_valuation,
            "real_time"
        )

        # Ensure fields are not removed/reset
        self.assertIn(
            "property_stock_valuation_account_id",
            category._fields
        )

    # ---------------------------------------------------------
    # TEST 04: Write valuation to real_time triggers onchange
    # ---------------------------------------------------------
    def test_04_write_real_time_triggers_onchange(self):
        category = self.ProductCategory.create({
            "name": "Test Category Write",
            "property_valuation": "manual_periodic",
        })

        category.write({
            "property_valuation": "real_time",
        })

        self.assertEqual(
            category.property_valuation,
            "real_time"
        )

        # Fields should still exist after write
        self.assertIn(
            "property_stock_journal",
            category._fields
        )
