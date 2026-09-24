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


class TestDashboardTheme(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.DashboardTheme = cls.env["dashboard.theme"]
        cls.DashboardThemeColor = cls.env["dashboard.theme.color"]

    # ---------------------------------------------------------
    # TEST 01: Create dashboard theme
    # ---------------------------------------------------------
    def test_01_create_dashboard_theme(self):
        theme = self.DashboardTheme.create({
            "name": "Default Theme",
            "background": "#ffffff",
            "title": "#000000",
            "subtitle": "#333333",
            "label_text": "Label",
            "border_width": 2,
            "border_color": "#dddddd",
        })

        self.assertTrue(theme)
        self.assertEqual(theme.name, "Default Theme")
        self.assertEqual(theme.background, "#ffffff")
        self.assertEqual(theme.border_width, 2)

    # ---------------------------------------------------------
    # TEST 02: Required field name
    # ---------------------------------------------------------
    def test_02_name_required(self):
        with self.assertRaises(Exception):
            self.DashboardTheme.create({
                "background": "#ffffff",
            })

    # ---------------------------------------------------------
    # TEST 03: Create theme colors
    # ---------------------------------------------------------
    def test_03_create_theme_colors(self):
        theme = self.DashboardTheme.create({
            "name": "Color Theme",
        })

        color1 = self.DashboardThemeColor.create({
            "name": "#ff0000",
            "theme_id": theme.id,
        })
        color2 = self.DashboardThemeColor.create({
            "name": "#00ff00",
            "theme_id": theme.id,
        })

        self.assertEqual(len(theme.theme_color_ids), 2)
        self.assertIn(color1, theme.theme_color_ids)
        self.assertIn(color2, theme.theme_color_ids)

    # ---------------------------------------------------------
    # TEST 04: read_theme() without colors
    # ---------------------------------------------------------
    def test_04_read_theme_without_colors(self):
        theme = self.DashboardTheme.create({
            "name": "Simple Theme",
        })

        data = theme.read_theme()

        self.assertEqual(data["name"], "Simple Theme")
        self.assertEqual(data["theme_color_ids"], [])
        self.assertEqual(data["body_header_background"], "#ecedcc")
        self.assertEqual(data["header_title_color"], "#000000")

    # ---------------------------------------------------------
    # TEST 05: read_theme() with colors
    # ---------------------------------------------------------
    def test_05_read_theme_with_colors(self):
        theme = self.DashboardTheme.create({
            "name": "Advanced Theme",
        })

        self.DashboardThemeColor.create({
            "name": "#111111",
            "theme_id": theme.id,
        })
        self.DashboardThemeColor.create({
            "name": "#222222",
            "theme_id": theme.id,
        })

        data = theme.read_theme()

        self.assertEqual(data["name"], "Advanced Theme")
        self.assertEqual(
            data["theme_color_ids"],
            ["#111111", "#222222"]
        )

    # ---------------------------------------------------------
    # TEST 06: Duplicate dashboard theme
    # ---------------------------------------------------------
    def test_06_duplicate_dashboard_theme(self):
        theme = self.DashboardTheme.create({
            "name": "Duplicate Theme",
            "background": "#fafafa",
        })

        duplicate = theme.copy()

        self.assertNotEqual(theme.id, duplicate.id)
        self.assertEqual(duplicate.name, theme.name)
        self.assertEqual(duplicate.background, theme.background)
