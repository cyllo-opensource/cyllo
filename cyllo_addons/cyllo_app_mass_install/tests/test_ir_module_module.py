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
from unittest.mock import patch


class TestIrModuleModule(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Module = cls.env['ir.module.module']
        cls.Category = cls.env['ir.module.category']

        # Create dummy category
        cls.parent_category = cls.Category.create({
            'name': 'Test Category',
        })

        # Create dummy module
        cls.test_module = cls.Module.create({
            'name': 'test_mass_install_module',
            'shortdesc': 'Test Module',
            'application': True,
            'state': 'uninstalled',
            'category_id': cls.parent_category.id,
        })

    # ---------------------------------------------------------
    # TEST 01: app_install triggers install method
    # ---------------------------------------------------------
    def test_01_app_install_calls_install(self):
        with patch.object(
            type(self.test_module),
            'button_immediate_install',
            return_value=True
        ) as mocked_install:
            self.Module.app_install([self.test_module.id])
            self.assertTrue(mocked_install.called)

    # ---------------------------------------------------------
    # TEST 02: get_child_app collects module ids
    # ---------------------------------------------------------
    def test_02_get_child_app(self):
        module_ids = []
        children_ids = [self.parent_category.id]

        result = self.Module.get_child_app(
            module_ids,
            children_ids
        )

        self.assertIn(self.test_module.id, result)

    # ---------------------------------------------------------
    # TEST 03: custom_data returns structured data
    # ---------------------------------------------------------
    def test_03_custom_data_structure(self):
        categories_with_app, categories_without_app = self.Module.custom_data()

        self.assertIsInstance(categories_with_app, list)
        self.assertIsInstance(categories_without_app, list)

        if categories_with_app:
            categ = categories_with_app[0]
            self.assertIn('id', categ)
            self.assertIn('name', categ)
            self.assertIn('child_apps', categ)

        if categories_without_app:
            categ = categories_without_app[0]
            self.assertIn('id', categ)
            self.assertIn('name', categ)
            self.assertIn('child_apps', categ)
