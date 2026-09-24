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


class TestIrModel(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.IrModel = cls.env["ir.model"]

    # ---------------------------------------------------------
    # TEST 01: get_model_from_table returns data when table exists
    # ---------------------------------------------------------
    def test_01_get_model_from_table_found(self):
        # Use an existing model (avoids x_ validation)
        model = self.IrModel.search(
            [("model", "=", "res.partner")],
            limit=1
        )
        self.assertTrue(model)

        # Set table_name explicitly for test
        model.write({"table_name": "res_partner"})

        with patch(
            "odoo.addons.cyllo_analytics.models.dashboard_sheet.DashboardSheet.get_data",
            return_value={"model_id": model.id}
        ):
            result = self.IrModel.get_model_from_table("res_partner")

        self.assertIsInstance(result, dict)
        self.assertEqual(result.get("model_id"), model.id)

    # ---------------------------------------------------------
    # TEST 02: get_model_from_table returns empty dict if not found
    # ---------------------------------------------------------
    def test_02_get_model_from_table_not_found(self):
        result = self.IrModel.get_model_from_table("non_existing_table")
        self.assertEqual(result, {})
