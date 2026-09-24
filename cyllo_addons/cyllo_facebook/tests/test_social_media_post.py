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


class TestSocialMediaPostFacebook(TransactionCase):
    """Covers social.fb.account's contribution to social.media.post's
    dashboard/connect dispatch hooks (moved here from
    cyllo_social_media_marketing when social.fb.account moved out)."""

    def setUp(self):
        super(TestSocialMediaPostFacebook, self).setUp()
        self.fb_account = self.env['social.fb.account'].create({
            'facebook_page_name': 'FB Page',
            'state': 'connected',
            'facebook_access_token': 'token',
            'facebook_user_access_token': 'token',
            'meta_app_number': '1',
            'meta_app_secret': '1',
            'company_id': self.env.company.id
        })

    def test_get_dashboard_data(self):
        """Test the Facebook tile in the aggregated dashboard data."""
        self.env['social.media.post'].create({
            'name': 'FB Post',
            'description': 'Test Content',
            'company_id': self.env.company.id,
            'user_id': self.env.user.id,
            'state': 'post',
            'fb_account_ids': [(6, 0, [self.fb_account.id])],
            'fb_likes_count': 10,
            'fb_comments_count': 5,
        })

        result = self.env['social.media.post'].get_dashboard_data()

        self.assertTrue(result)
        self.assertIn('dashboard_data', result)

        data = result['dashboard_data']
        fb_data = next(
            (d for d in data if d['platform'] == 'social.fb.account'), None
        )
        self.assertIsNotNone(fb_data)
        self.assertEqual(fb_data['account_name'], 'FB Page')
        self.assertEqual(fb_data['total_likes'], 10)
        self.assertEqual(fb_data['total_comments'], 5)

    @patch(
        'odoo.addons.cyllo_facebook.models.social_fb_account.SocialFbAccount.action_connect')
    def test_action_create_connect_fb(self, mock_connect):
        """Test creating and connecting FB account via the post model helper"""
        data = {
            'facebook_page_name': 'New FB',
            'facebook_access_token': 't',
            'facebook_user_access_token': 't',
            'meta_app_number': '1',
            'meta_app_secret': '1',
            'company_id': self.env.company.id
        }

        self.env['social.media.post'].action_create_connect(data, 'social.fb.account')
        mock_connect.assert_called_once()

        account = self.env['social.fb.account'].search(
            [('facebook_page_name', '=', 'New FB')])
        self.assertTrue(account)
