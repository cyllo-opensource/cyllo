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


class TestDashboardSheetOption(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.DashboardSheetOption = cls.env["dashboard.sheet.option"]
        cls.DashboardSheet = cls.env["dashboard.sheet"]
        cls.DashboardConfig = cls.env["dashboard.config"]

        cls.dashboard_config = cls.DashboardConfig.create({
            "name": "Test Dashboard Config",
        })

        cls.dashboard_sheet = cls.DashboardSheet.create({
            "name": "Test Sheet",
            "type": "bar",
        })

    # ---------------------------------------------------------
    # TEST 01: Create dashboard sheet option
    # ---------------------------------------------------------
    def test_01_create_dashboard_sheet_option(self):
        option = self.DashboardSheetOption.create({
            "dashboard_sheet_id": self.dashboard_sheet.id,
            "dashboard_config_id": self.dashboard_config.id,
            "attributes": {
                "x": 0,
                "y": 1,
                "graph_width": 4,
                "graph_height": 2,
            },
        })

        self.assertTrue(option)
        self.assertEqual(option.dashboard_sheet_id.id, self.dashboard_sheet.id)
        self.assertEqual(option.dashboard_config_id.id, self.dashboard_config.id)
        self.assertEqual(option.attributes["x"], 0)
        self.assertEqual(option.attributes["graph_width"], 4)

    # ---------------------------------------------------------
    # TEST 02: Write attributes
    # ---------------------------------------------------------
    def test_02_write_dashboard_sheet_option(self):
        option = self.DashboardSheetOption.create({
            "dashboard_sheet_id": self.dashboard_sheet.id,
            "dashboard_config_id": self.dashboard_config.id,
            "attributes": {"x": 1, "y": 1},
        })

        option.write({
            "attributes": {"x": 5, "y": 6}
        })

        self.assertEqual(option.attributes["x"], 5)
        self.assertEqual(option.attributes["y"], 6)

    # ---------------------------------------------------------
    # TEST 03: Allow empty attributes
    # ---------------------------------------------------------
    def test_03_empty_attributes(self):
        option = self.DashboardSheetOption.create({
            "dashboard_sheet_id": self.dashboard_sheet.id,
            "dashboard_config_id": self.dashboard_config.id,
        })

        self.assertTrue(option)
        self.assertFalse(option.attributes)
