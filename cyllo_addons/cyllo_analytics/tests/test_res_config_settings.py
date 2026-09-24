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
from odoo.exceptions import ValidationError


class TestResConfigSettings(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Settings = cls.env["res.config.settings"]

    # ---------------------------------------------------------
    # TEST 01: Save and retrieve OpenAI API key config parameter
    # ---------------------------------------------------------
    def test_01_openai_api_key_config(self):
        settings = self.Settings.create({
            "openai_api_key": "test-api-key-123",
        })
        settings.execute()

        value = self.env["ir.config_parameter"].sudo().get_param(
            "cyllo_analytics.openai_api_key"
        )
        self.assertEqual(value, "test-api-key-123")

    # ---------------------------------------------------------
    # TEST 02: Financial year config parameters saved correctly
    # ---------------------------------------------------------
    def test_02_financial_year_settings(self):
        settings = self.Settings.create({
            "is_financial_year": True,
            "fiscal_year_last_month": "3",
            "fiscal_year_last_day": 31,
        })
        settings.execute()

        params = self.env["ir.config_parameter"].sudo()
        self.assertEqual(
            params.get_param("cyllo_analytics.is_financial_year"), "True"
        )
        self.assertEqual(
            params.get_param("cyllo_analytics.fiscal_year_last_month"), "3"
        )
        self.assertEqual(
            params.get_param("cyllo_analytics.fiscal_year_last_day"), "31"
        )

    # ---------------------------------------------------------
    # TEST 03: Limit record configuration
    # ---------------------------------------------------------
    def test_03_limit_record_settings(self):
        settings = self.Settings.create({
            "limit_record": True,
            "limit": 500,
        })
        settings.execute()

        params = self.env["ir.config_parameter"].sudo()
        self.assertEqual(
            params.get_param("cyllo_analytics.limit_record"), "True"
        )
        self.assertEqual(
            params.get_param("cyllo_analytics.limit"), "500"
        )

    # ---------------------------------------------------------
    # TEST 04: Invalid fiscal year last day should raise error
    # ---------------------------------------------------------
    def test_04_invalid_fiscal_year_last_day(self):
        with self.assertRaises(ValidationError):
            self.Settings.create({
                "fiscal_year_last_month": "2",  # February
                "fiscal_year_last_day": 31,     # Invalid
            })
