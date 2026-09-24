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


class TestResPartnerInstagram(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.insta_account = cls.env["social.insta.account"].create({
            "instagram_account_number": "1234567890",
            "instagram_business_account_number": "1234567890",

            "instagram_access_token": "TEST_LONG_LIVED_TOKEN",
            "instagram_page_access_token": "TEST_PAGE_ACCESS_TOKEN",

            "facebook_insta_page_name": "Test Instagram Page",
            "meta_app_number": "TEST_META_APP_ID",
            "meta_app_secret": "TEST_META_APP_SECRET",

            "instagram_base_url": "https://graph.facebook.com/v19.0",

            "state": "connected",
        })

        cls.partner = cls.env["res.partner"].create({
            "name": "Instagram Partner",
            "unique_ig_number": "999888777",
            "insta_account_id": cls.insta_account.id,
        })


    @patch("odoo.addons.cyllo_instagram.models.res_partner.requests.post")
    def test_action_message_partner_insta(self, mock_post):

        response = self.partner.action_message_partner_insta(
            "Hello from test case"
        )

        self.assertTrue(self.partner.is_insta_chat)
        self.assertEqual(self.partner.insta_chat, "Hello from test case")
        self.assertTrue(self.partner.insta_chat_time)

        self.assertEqual(mock_post.call_count, 1)

        args, kwargs = mock_post.call_args
        self.assertIn("access_token=TEST_PAGE_ACCESS_TOKEN", args[0])
        self.assertEqual(kwargs["json"]["recipient"]["id"], "999888777")
        self.assertEqual(kwargs["json"]["message"]["text"], "Hello from test case")

        self.assertEqual(response["type"], "ir.actions.client")
        self.assertEqual(response["tag"], "display_notification")
        self.assertEqual(response["params"]["type"], "success")
