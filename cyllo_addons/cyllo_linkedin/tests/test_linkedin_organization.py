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


class TestLinkedinOrganization(TransactionCase):

    def setUp(self):
        super().setUp()

        self.account = self.env["linkedin.account"].create({
            "name": "Test Account",
            "linkedin_access_token": "dummy_token",
            "state": "connected",
            "company_id": self.env.company.id,
        })

        self.organization = self.env["linkedin.organization"].create({
            "name": "Test Organization",
            "org_urn": "urn:li:organization:12345",
            "account_id": self.account.id,
        })

    def test_get_org_data(self):
        data = self.organization.get_org_data()

        self.assertEqual(data["id"], self.organization.id)
        self.assertEqual(data["name"], self.organization.name)
        self.assertEqual(data["org_urn"], self.organization.org_urn)

    def test_feed_count(self):
        self.organization._compute_feed_count()
        self.assertEqual(self.organization.feed_count, 0)

    @patch(
        "odoo.addons.cyllo_linkedin.models.linkedin_account.LinkedInAccount._fetch_feeds_for_urn"
    )
    def test_action_fetch_feeds(self, mock_fetch):
        mock_fetch.return_value = 5

        result = self.organization.action_fetch_feeds()

        self.assertEqual(result["type"], "ir.actions.client")
        self.assertEqual(result["tag"], "display_notification")
        mock_fetch.assert_called_once()