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


class TestMailMessageInstagram(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.partner = cls.env["res.partner"].create({
            "name": "Instagram User",
            "email": "1234567890",
        })

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

        cls.message = cls.env["mail.message"].create({
            "author_id": cls.partner.id,
            "email_from": "1234567890",
            "body": "Hello from Instagram",
            "is_from_insta": True,
            "insta_sender_number": "1234567890",
        })

    @patch("odoo.addons.cyllo_instagram.models.mail_message.requests.post")
    def test_action_reply_message_insta(self, mock_post):
        response = self.message.action_reply_message("Reply from test")

        self.assertEqual(mock_post.call_count, 1)
        args, kwargs = mock_post.call_args

        self.assertIn("access_token=TEST_PAGE_ACCESS_TOKEN", args[0])
        self.assertEqual(kwargs["json"]["recipient"]["id"], "1234567890")
        self.assertEqual(kwargs["json"]["message"]["text"], "Reply from test")
        self.assertEqual(response["params"]["type"], "success")

    def test_action_create_lead_from_instagram(self):
        lead = self.env["crm.lead"].browse(
            self.message.action_create_lead()
        )
        self.assertTrue(lead.exists())
        self.assertEqual(lead.insta_user_number, "1234567890")

    @patch("odoo.addons.cyllo_instagram.models.mail_message.requests.post")
    def test_action_reply_message_chatter_insta(self, mock_post):
        lead = self.env["crm.lead"].create({
            "name": "Instagram Lead",
            "type": "lead",
        })

        response = self.message.action_reply_message_chatter(
            sender_id="1234567890",
            reply="Reply from chatter",
            res_id=lead.id,
        )

        self.assertEqual(mock_post.call_count, 1)
        self.assertEqual(response["params"]["type"], "success")
