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
from psycopg2 import IntegrityError


class TestIrActionsActWindowView(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.ActWindow = cls.env["ir.actions.act_window"]
        cls.ActWindowView = cls.env["ir.actions.act_window.view"]
        cls.View = cls.env["ir.ui.view"]

    # ---------------------------------------------------------
    # TEST 01: Create act_window_view with tile view_mode
    # ---------------------------------------------------------
    def test_01_create_tile_view_mode(self):
        view = self.View.create({
            "name": "Tile View",
            "type": "qweb",
            "arch": "<templates/>",
        })

        action = self.ActWindow.create({
            "name": "Test Action",
            "res_model": "res.partner",
        })

        act_view = self.ActWindowView.create({
            "sequence": 10,
            "view_mode": "tile",
            "view_id": view.id,
            "act_window_id": action.id,
        })

        self.assertTrue(act_view)
        self.assertEqual(act_view.view_mode, "tile")

    # ---------------------------------------------------------
    # TEST 02: Ensure tile exists in selection
    # ---------------------------------------------------------
    def test_02_tile_in_view_mode_selection(self):
        selection = dict(
            self.ActWindowView._fields["view_mode"].selection
        )

        self.assertIn("tile", selection)
        self.assertEqual(selection["tile"], "Tile")

    # ---------------------------------------------------------
    # TEST 03: Copy act_window_view with tile mode (blocked)
    # ---------------------------------------------------------
    def test_03_copy_tile_view_blocked(self):
        view = self.View.create({
            "name": "Tile View",
            "type": "qweb",
            "arch": "<templates/>",
        })

        action = self.ActWindow.create({
            "name": "Tile Action",
            "res_model": "res.partner",
        })

        act_view = self.ActWindowView.create({
            "view_mode": "tile",
            "view_id": view.id,
            "act_window_id": action.id,
        })

        # Copy should FAIL due to unique constraint
        with self.assertRaises(IntegrityError):
            act_view.copy()
