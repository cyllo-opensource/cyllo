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


class TestDashboardSheetType(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.DashboardSheetType = cls.env["dashboard.sheet.type"]

    # ---------------------------------------------------------
    # TEST 01: Create dashboard sheet type
    # ---------------------------------------------------------
    def test_01_create_sheet_type(self):
        sheet_type = self.DashboardSheetType.create({
            "name": "Bar Chart",
            "ttype": "bar",
        })

        self.assertTrue(sheet_type)
        self.assertEqual(sheet_type.name, "Bar Chart")
        self.assertEqual(sheet_type.ttype, "bar")

    # ---------------------------------------------------------
    # TEST 02: Required field ttype
    # ---------------------------------------------------------
    def test_02_ttype_required(self):
        with self.assertRaises(Exception):
            self.DashboardSheetType.create({
                "name": "Invalid Type",
            })

    # ---------------------------------------------------------
    # TEST 03: Write sheet type values
    # ---------------------------------------------------------
    def test_03_write_sheet_type(self):
        sheet_type = self.DashboardSheetType.create({
            "name": "Pie Chart",
            "ttype": "pie",
        })

        sheet_type.write({
            "name": "Updated Pie Chart",
            "ttype": "donut",
        })

        self.assertEqual(sheet_type.name, "Updated Pie Chart")
        self.assertEqual(sheet_type.ttype, "donut")

    # ---------------------------------------------------------
    # TEST 04: Duplicate sheet type
    # ---------------------------------------------------------
    def test_04_duplicate_sheet_type(self):
        sheet_type = self.DashboardSheetType.create({
            "name": "Line Chart",
            "ttype": "line",
        })

        duplicate = sheet_type.copy()

        self.assertNotEqual(sheet_type.id, duplicate.id)
        self.assertEqual(duplicate.name, sheet_type.name)
        self.assertEqual(duplicate.ttype, sheet_type.ttype)
