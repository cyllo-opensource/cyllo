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


class TestIrUiMenu(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Menu = cls.env["ir.ui.menu"]

    # ---------------------------------------------------------
    # TEST 01: Create menu with is_cyllo_analytic_menu = True
    # ---------------------------------------------------------
    def test_01_create_cyllo_analytic_menu(self):
        menu = self.Menu.create({
            "name": "Cyllo Analytics Menu",
            "is_cyllo_analytic_menu": True,
        })

        self.assertTrue(menu)
        self.assertTrue(menu.is_cyllo_analytic_menu)

    # ---------------------------------------------------------
    # TEST 02: Default value should be False
    # ---------------------------------------------------------
    def test_02_default_is_cyllo_analytic_menu_false(self):
        menu = self.Menu.create({
            "name": "Normal Menu",
        })

        self.assertFalse(menu.is_cyllo_analytic_menu)

    # ---------------------------------------------------------
    # TEST 03: Update is_cyllo_analytic_menu field
    # ---------------------------------------------------------
    def test_03_update_cyllo_analytic_menu(self):
        menu = self.Menu.create({
            "name": "Updatable Menu",
        })

        self.assertFalse(menu.is_cyllo_analytic_menu)

        menu.write({"is_cyllo_analytic_menu": True})
        self.assertTrue(menu.is_cyllo_analytic_menu)
