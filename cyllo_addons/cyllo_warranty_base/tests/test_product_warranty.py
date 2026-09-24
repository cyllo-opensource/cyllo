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

from datetime import date

from odoo import fields
from odoo.tests import tagged

from .test_common import WarrantyBaseTestCommon


@tagged('post_install', '-at_install')
class TestProductCategory(WarrantyBaseTestCommon):
    """Tests for warranty fields on product.category."""

    def test_category_warranty_defaults(self):
        """Verify default warranty field values on a new category."""
        category = self.env['product.category'].create({
            'name': 'Default Category',
        })
        self.assertEqual(category.warranty_period, 0,
                         "Default warranty period should be 0")
        self.assertEqual(category.warranty_period_unit, 'month',
                         "Default warranty unit should be 'month'")

    def test_category_warranty_values(self):
        """Verify warranty fields are correctly stored on category."""
        self.assertEqual(self.category_warranty.warranty_period, 12)
        self.assertEqual(self.category_warranty.warranty_period_unit, 'month')

    def test_category_warranty_update(self):
        """Verify warranty fields can be updated on category."""
        self.category_warranty.write({
            'warranty_period': 2,
            'warranty_period_unit': 'year',
        })
        self.assertEqual(self.category_warranty.warranty_period, 2)
        self.assertEqual(self.category_warranty.warranty_period_unit, 'year')

    def test_category_warranty_all_units(self):
        """Verify all warranty unit options work on category."""
        for unit in ('day', 'month', 'year'):
            self.category_warranty.warranty_period_unit = unit
            self.assertEqual(self.category_warranty.warranty_period_unit, unit)


@tagged('post_install', '-at_install')
class TestProductTemplate(WarrantyBaseTestCommon):
    """Tests for warranty fields on product.template."""

    def test_template_warranty_defaults(self):
        """Verify default warranty field values on a new product template."""
        template = self.env['product.template'].create({
            'name': 'Bare Product',
            'type': 'consu',
        })
        self.assertEqual(template.warranty_period, 0,
                         "Default warranty period should be 0")
        self.assertEqual(template.warranty_period_unit, 'month',
                         "Default warranty unit should be 'month'")

    def test_template_warranty_values(self):
        """Verify warranty fields are correctly stored on template."""
        self.assertEqual(
            self.product_template_warranty.warranty_period, 24)
        self.assertEqual(
            self.product_template_warranty.warranty_period_unit, 'month')

    def test_template_warranty_update(self):
        """Verify warranty fields can be updated on product template."""
        self.product_template_warranty.write({
            'warranty_period': 365,
            'warranty_period_unit': 'day',
        })
        self.assertEqual(
            self.product_template_warranty.warranty_period, 365)
        self.assertEqual(
            self.product_template_warranty.warranty_period_unit, 'day')


@tagged('post_install', '-at_install')
class TestProductWarrantyDefinition(WarrantyBaseTestCommon):
    """Tests for _get_warranty_definition on product.product."""

    def test_warranty_definition_from_template(self):
        """Product with own warranty should return template values."""
        period, unit = self.product_own_warranty._get_warranty_definition()
        self.assertEqual(period, 24)
        self.assertEqual(unit, 'month')

    def test_warranty_definition_fallback_to_category(self):
        """Product without own warranty should fall back to category."""
        period, unit = self.product_category_warranty._get_warranty_definition()
        self.assertEqual(period, 12)
        self.assertEqual(unit, 'month')

    def test_warranty_definition_no_warranty(self):
        """Product with no warranty anywhere should return (0, 'month')."""
        period, unit = self.product_no_warranty._get_warranty_definition()
        self.assertEqual(period, 0)
        self.assertEqual(unit, 'month')

    def test_warranty_definition_template_overrides_category(self):
        """Template warranty should take precedence over category warranty."""
        # product_own_warranty is in category_warranty (12 months)
        # but its template has 24 months — template should win
        period, unit = self.product_own_warranty._get_warranty_definition()
        self.assertEqual(period, 24,
                         "Template warranty should override category warranty")

    def test_warranty_definition_category_day_unit(self):
        """Category with 'day' unit should propagate correctly."""
        self.category_warranty.write({
            'warranty_period': 90,
            'warranty_period_unit': 'day',
        })
        period, unit = self.product_category_warranty._get_warranty_definition()
        self.assertEqual(period, 90)
        self.assertEqual(unit, 'day')

    def test_warranty_definition_category_year_unit(self):
        """Category with 'year' unit should propagate correctly."""
        self.category_warranty.write({
            'warranty_period': 3,
            'warranty_period_unit': 'year',
        })
        period, unit = self.product_category_warranty._get_warranty_definition()
        self.assertEqual(period, 3)
        self.assertEqual(unit, 'year')


@tagged('post_install', '-at_install')
class TestProductWarrantyExpiration(WarrantyBaseTestCommon):
    """Tests for _get_warranty_expiration_date on product.product."""

    def test_expiration_date_months(self):
        """Warranty in months should add correct months to start date."""
        start = date(2026, 1, 15)
        expiry = self.product_own_warranty._get_warranty_expiration_date(start)
        self.assertEqual(expiry, date(2028, 1, 15),
                         "24-month warranty from 2026-01-15 → 2028-01-15")

    def test_expiration_date_days(self):
        """Warranty in days should add correct days to start date."""
        self.product_template_warranty.write({
            'warranty_period': 30,
            'warranty_period_unit': 'day',
        })
        start = date(2026, 3, 1)
        expiry = self.product_own_warranty._get_warranty_expiration_date(start)
        self.assertEqual(expiry, date(2026, 3, 31),
                         "30-day warranty from 2026-03-01 → 2026-03-31")

    def test_expiration_date_years(self):
        """Warranty in years should add correct years to start date."""
        self.product_template_warranty.write({
            'warranty_period': 2,
            'warranty_period_unit': 'year',
        })
        start = date(2026, 6, 1)
        expiry = self.product_own_warranty._get_warranty_expiration_date(start)
        self.assertEqual(expiry, date(2028, 6, 1),
                         "2-year warranty from 2026-06-01 → 2028-06-01")

    def test_expiration_date_no_warranty(self):
        """Product with no warranty should return False."""
        start = date(2026, 1, 1)
        expiry = self.product_no_warranty._get_warranty_expiration_date(start)
        self.assertFalse(expiry,
                         "No warranty defined → expiration should be False")

    def test_expiration_date_no_start_date(self):
        """Passing no start date should return False."""
        expiry = self.product_own_warranty._get_warranty_expiration_date(False)
        self.assertFalse(expiry,
                         "No start date → expiration should be False")

    def test_expiration_date_none_start_date(self):
        """Passing None as start date should return False."""
        expiry = self.product_own_warranty._get_warranty_expiration_date(None)
        self.assertFalse(expiry,
                         "None start date → expiration should be False")

    def test_expiration_date_string_start_date(self):
        """String date should be accepted and converted correctly."""
        expiry = self.product_own_warranty._get_warranty_expiration_date(
            '2026-01-15')
        self.assertEqual(expiry, date(2028, 1, 15),
                         "String date should be handled via fields.Date.to_date")

    def test_expiration_date_category_fallback(self):
        """Expiration should use category warranty when template has none."""
        start = date(2026, 6, 1)
        expiry = self.product_category_warranty._get_warranty_expiration_date(
            start)
        # category_warranty has 12 months
        self.assertEqual(expiry, date(2027, 6, 1),
                         "12-month category warranty from 2026-06-01 → 2027-06-01")

    def test_expiration_date_end_of_month(self):
        """Verify month-end edge case (e.g. Jan 31 + 1 month = Feb 28)."""
        self.product_template_warranty.write({
            'warranty_period': 1,
            'warranty_period_unit': 'month',
        })
        start = date(2026, 1, 31)
        expiry = self.product_own_warranty._get_warranty_expiration_date(start)
        self.assertEqual(expiry, date(2026, 2, 28),
                         "Jan 31 + 1 month should clamp to Feb 28")

    def test_expiration_date_leap_year(self):
        """Verify leap year edge case (Feb 29 + 1 year)."""
        self.product_template_warranty.write({
            'warranty_period': 1,
            'warranty_period_unit': 'year',
        })
        start = date(2028, 2, 29)  # 2028 is a leap year
        expiry = self.product_own_warranty._get_warranty_expiration_date(start)
        # 2029 is not a leap year, so Feb 29 → Feb 28
        self.assertEqual(expiry, date(2029, 2, 28),
                         "Feb 29 + 1 year should clamp to Feb 28")

    def test_expiration_date_zero_period(self):
        """Zero period on template but positive on category should use category."""
        self.product_template_category_warranty.warranty_period = 0
        start = date(2026, 1, 1)
        expiry = self.product_category_warranty._get_warranty_expiration_date(
            start)
        self.assertEqual(expiry, date(2027, 1, 1),
                         "Should fall back to 12-month category warranty")
