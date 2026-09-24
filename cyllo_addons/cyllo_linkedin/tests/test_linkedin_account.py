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
from unittest.mock import patch

from odoo.tests.common import TransactionCase


class TestLinkedinAccount(TransactionCase):

    def setUp(self):
        super().setUp()

        self.company = self.env.company

    @patch(
        "odoo.addons.cyllo_linkedin.models.linkedin_account.LinkedInAccount.action_sync_organizations"
    )
    def test_create_account_with_access_token(self, mock_sync):
        account = self.env["linkedin.account"].create({
            "name": "Test LinkedIn",
            "linkedin_access_token": "dummy_token",
            "company_id": self.company.id,
        })

        self.assertEqual(account.state, "connected")
        mock_sync.assert_called_once()

    def test_create_account_without_access_token(self):
        account = self.env["linkedin.account"].create({
            "name": "Test LinkedIn",
            "company_id": self.company.id,
        })

        self.assertEqual(account.state, "not connected")

    def test_compute_is_default(self):
        account = self.env["linkedin.account"].create({
            "name": "Default Account",
            "company_id": self.company.id,
        })

        self.env["ir.config_parameter"].sudo().set_param(
            "social_linkedin_account.default_account_id",
            account.id,
        )

        account._compute_is_default()

        self.assertTrue(account.is_default)