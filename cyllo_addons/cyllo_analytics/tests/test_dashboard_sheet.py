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


class TestDashboardSheet(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.DashboardSheet = cls.env["dashboard.sheet"]

    # ---------------------------------------------------------
    # TEST 01: Create dashboard sheet
    # ---------------------------------------------------------
    def test_01_create_dashboard_sheet(self):
        sheet = self.DashboardSheet.create({
            "name": "Sales Sheet",
            "type": "bar",
            "limit": 10,
        })

        self.assertTrue(sheet)
        self.assertEqual(sheet.name, "Sales Sheet")
        self.assertEqual(sheet.type, "bar")
        self.assertEqual(sheet.limit, 10)

    # ---------------------------------------------------------
    # TEST 02: Limit is stored as-is
    # ---------------------------------------------------------
    def test_02_limit_value(self):
        sheet = self.DashboardSheet.create({
            "name": "Limit Sheet",
            "type": "bar",
            "limit": 500,
        })

        self.assertEqual(sheet.limit, 500)

    # ---------------------------------------------------------
    # TEST 03: Write limit
    # ---------------------------------------------------------
    def test_03_write_limit(self):
        sheet = self.DashboardSheet.create({
            "name": "Write Limit Sheet",
            "type": "pie",
            "limit": 20,
        })

        sheet.write({"limit": 999})
        self.assertEqual(sheet.limit, 999)

    # ---------------------------------------------------------
    # TEST 04: Duplicate sheet
    # ---------------------------------------------------------
    def test_04_duplicate_sheet(self):
        sheet = self.DashboardSheet.create({
            "name": "Original Sheet",
            "type": "bar",
        })

        duplicate = sheet.copy()

        self.assertNotEqual(sheet.id, duplicate.id)
        self.assertEqual(duplicate.name, sheet.name)

    # ---------------------------------------------------------
    # TEST 05: GPT token counter (mocked)
    # ---------------------------------------------------------
    def test_05_token_counter(self):
        sheet = self.DashboardSheet.create({
            "name": "Token Sheet",
            "type": "bar",
        })

        with patch(
                "odoo.addons.cyllo_analytics.models.dashboard_sheet.DashboardSheet.count_gpt_tokens",
                return_value=42
        ):
            tokens = sheet.count_gpt_tokens("SELECT * FROM res_partner")

        self.assertEqual(tokens, 42)

    # ---------------------------------------------------------
    # TEST 06: Base prompt generation
    # ---------------------------------------------------------
    def test_06_base_prompt(self):
        sheet = self.DashboardSheet.create({
            "name": "Prompt Sheet",
            "type": "bar",
        })

        prompt = sheet.get_base_prompt(
            "SELECT count(*) FROM res_partner"
        )

        self.assertIn("SELECT", prompt)
