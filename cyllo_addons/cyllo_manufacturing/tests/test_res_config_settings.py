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
from odoo.tests import common, tagged


@tagged('post_install', '-at_install')
class TestResConfigSettings(common.TransactionCase):
    """Tests for the res.config.settings manufacturing extensions."""

    def _get_settings(self, **extra):
        """Create and return a res.config.settings record."""
        return self.env['res.config.settings'].create(extra)

    def test_01_shopfloor_field_exists(self):
        """The module_cyllo_shopfloor boolean should be present."""
        settings = self._get_settings()
        self.assertFalse(
            settings.module_cyllo_shopfloor,
            "module_cyllo_shopfloor should default to False.",
        )

    def test_02_quality_mrp_field_exists(self):
        """The module_cyllo_quality_mrp boolean should be present."""
        settings = self._get_settings()
        self.assertFalse(
            settings.module_cyllo_quality_mrp,
            "module_cyllo_quality_mrp should default to False.",
        )

    def test_03_toggle_shopfloor(self):
        """Setting module_cyllo_shopfloor to True should persist correctly."""
        settings = self._get_settings(module_cyllo_shopfloor=True)
        self.assertTrue(settings.module_cyllo_shopfloor)

    def test_04_toggle_quality_mrp(self):
        """Setting module_cyllo_quality_mrp to True should persist correctly."""
        settings = self._get_settings(module_cyllo_quality_mrp=True)
        self.assertTrue(settings.module_cyllo_quality_mrp)

    def test_05_both_toggles_independent(self):
        """Both module toggles should be independently settable."""
        settings = self._get_settings(
            module_cyllo_shopfloor=True,
            module_cyllo_quality_mrp=False,
        )
        self.assertTrue(settings.module_cyllo_shopfloor)
        self.assertFalse(settings.module_cyllo_quality_mrp)

        settings2 = self._get_settings(
            module_cyllo_shopfloor=False,
            module_cyllo_quality_mrp=True,
        )
        self.assertFalse(settings2.module_cyllo_shopfloor)
        self.assertTrue(settings2.module_cyllo_quality_mrp)

    def test_06_settings_inherit_mrp(self):
        """res.config.settings should still inherit from mrp's settings."""
        fields_info = self.env['res.config.settings'].fields_get()
        self.assertIn('module_cyllo_shopfloor', fields_info)
        self.assertIn('module_cyllo_quality_mrp', fields_info)
        # Verify field type is boolean
        self.assertEqual(fields_info['module_cyllo_shopfloor']['type'],
                         'boolean')
        self.assertEqual(fields_info['module_cyllo_quality_mrp']['type'],
                         'boolean')
