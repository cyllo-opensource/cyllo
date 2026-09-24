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


class TestRecruitmentConfig(TransactionCase):

    def test_set_and_get_values(self):
        settings = self.env["res.config.settings"].create({
            "li_username": "test_user",
            "li_password": "test_password",
        })

        settings.set_values()

        self.assertEqual(
            self.env["ir.config_parameter"].sudo().get_param(
                "recruitment.li_username"
            ),
            "test_user",
        )

        self.assertEqual(
            self.env["ir.config_parameter"].sudo().get_param(
                "recruitment.li_password"
            ),
            "test_password",
        )

        values = settings.get_values()

        self.assertEqual(values["li_username"], "test_user")
        self.assertEqual(values["li_password"], "test_password")