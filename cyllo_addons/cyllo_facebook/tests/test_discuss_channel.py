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


class TestDiscussChannelFacebook(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.user = cls.env.user

        cls.partner = cls.env['res.partner'].create({
            'name': 'Facebook Partner',
        })

        cls.fb_account = cls.env['social.fb.account'].create({
            'facebook_page_name': 'Test Facebook Page',
            'facebook_access_token': 'page_test_token',
            'facebook_user_access_token': 'user_test_token',
            'facebook_base_url': 'https://graph.facebook.com/v18.0',
            'state': 'connected',
            'meta_app_number': 'test_meta_app_001',
            'meta_app_secret': 'test_meta_app_secret',
        })

        cls.partner.fb_account_id = cls.fb_account.id

        cls.channel = cls.env['discuss.channel'].create({
            'name': 'Facebook Test Channel',
            'channel_partner_ids': [
                (4, cls.partner.id),
                (4, cls.user.partner_id.id),
            ],
            'fb_partner_number': '123456789',
        })

    def test_action_find_partner_fb(self):
        result = self.channel.action_find_partner_fb()

        self.assertIn('partner', result)
        self.assertIn('facebook', result)
        self.assertEqual(result['facebook'], '123456789')
        self.assertNotIn(self.user.partner_id, result['partner'])

    @patch('odoo.addons.cyllo_facebook.models.discuss_channel.requests.post')
    def test_action_message_chat_discuss_fb(self, mock_post):

        mock_post.return_value.status_code = 200

        result = self.channel.action_message_chat_discuss_fb(
            "Hello from Odoo!"
        )

        mock_post.assert_called_once()
        self.assertEqual(result['tag'], 'display_notification')
        self.assertEqual(result['params']['type'], 'success')
        self.assertEqual(
            result['params']['message'],
            'Reply has been sent'
        )
