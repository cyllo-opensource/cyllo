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
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from odoo.tests import common
from odoo.exceptions import ValidationError

class TestYoutubeAccount(common.TransactionCase):
    """
    Test cases for 'youtube.account' model, covering OAuth authentication,
    token lifecycle management, and channel synchronization.
    """

    def setUp(self):
        """
        Setup test environment for YouTube account tests, including 
        initial state.
        """
        super().setUp()
        self.youtube_account = self.env['youtube.account'].create({
            'name': 'Test YouTube Account',
            'client_number': 'test_client_id_123',
            'client_secret': 'test_client_secret_456',
            'company_id': self.env.company.id,
        })

    def test_youtube_account_creation(self):
        """
        Test the successful creation of a YouTube account in 'new' state.
        """
        self.assertEqual(self.youtube_account.state, 'new')
        self.assertFalse(self.youtube_account.access_token)

    def test_get_authorization_url(self):
        """
        Test the generation of the Google OAuth authorization URL.
        """
        result = self.youtube_account.action_get_authorization_url()
        self.assertEqual(result['type'], 'ir.actions.act_url')
        self.assertIn('accounts.google.com/o/oauth2/auth', result['url'])

    @patch('requests.post')
    def test_authenticate_with_youtube_success(self, mock_post):
        """
        Test successful authentication and token acquisition from YouTube.
        """
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                'access_token': 'access_token',
                'refresh_token': 'refresh_token',
                'expires_in': 3600,
            }
        )

        self.youtube_account.authenticate_with_youtube('auth_code')
        self.assertEqual(self.youtube_account.state, 'sync')
        self.assertTrue(self.youtube_account.token_expiry_date)

    @patch('requests.post')
    def test_authenticate_with_youtube_failure(self, mock_post):
        """
        Test behavior when YouTube authentication fails with an invalid code.
        """
        mock_post.return_value = MagicMock(
            status_code=400,
            json=lambda: {'error_description': 'Invalid code'}
        )
        with self.assertRaises(ValidationError):
            self.youtube_account.authenticate_with_youtube('bad_code')

    @patch('requests.post')
    def test_refresh_access_token_success(self, mock_post):
        """
        Test successful refreshing of an expired access token using a refresh token.
        """
        self.youtube_account.refresh_token = 'refresh_token'
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                'access_token': 'new_access_token',
                'expires_in': 3600,
            }
        )

        self.youtube_account.action_refresh_access_token()
        self.assertEqual(self.youtube_account.access_token, 'new_access_token')

    @patch('requests.post')
    def test_refresh_access_token_failure(self, mock_post):
        """
        Test behavior when token refreshing fails due to an invalid refresh token.
        """
        self.youtube_account.refresh_token = 'bad_token'
        mock_post.return_value = MagicMock(
            status_code=400,
            json=lambda: {'error_description': 'Invalid refresh token'}
        )
        with self.assertRaises(ValidationError):
            self.youtube_account.action_refresh_access_token()

    def test_action_disconnect(self):
        """
        Test disconnecting a YouTube account and deactivating linked channels.
        """
        channel = self.env['youtube.channel'].create({
            'name': 'Test Channel',
            'youtube_account_id': self.youtube_account.id,
            'youtube_number': 'channel_1',
            'youtube_etag': 'etag',
            'customUrl': 'test_channel_url',
            'is_active': True,
        })

        self.youtube_account.write({'state': 'sync'})
        self.youtube_account.action_disconnect()

        channel = self.env['youtube.channel'].browse(channel.id)
        self.assertEqual(self.youtube_account.state, 'new')
        self.assertFalse(channel.is_active)

    @patch('requests.get')
    def test_get_channel_details_success(self, mock_get):
        """
        Test successful retrieval and storage of YouTube channel metadata.
        """
        self.youtube_account.access_token = 'token'
        self.youtube_account.token_expiry_date = datetime.now() + timedelta(hours=1)

        channel_api_response = MagicMock()
        channel_api_response.status_code = 200
        channel_api_response.json.return_value = {
            'items': [{
                'id': 'channel_123',
                'etag': 'etag_123',
                'snippet': {
                    'title': 'Test Channel',
                    'customUrl': 'custom_url',
                    'thumbnails': {'default': {'url': 'https://example.com/image.jpg'}}
                }
            }]
        }

        image_response = MagicMock()
        image_response.content = b'test-image-bytes'

        mock_get.side_effect = [channel_api_response, image_response]

        self.youtube_account.action_get_channel_details()
        channel = self.env['youtube.channel'].search([('youtube_number', '=', 'channel_123')])
        self.assertTrue(channel)
        self.assertEqual(self.youtube_account.channel_count, 1)

    def test_action_open_channel(self):
        """
        Test the action that opens the linked YouTube channels view.
        """
        result = self.youtube_account.action_open_channel()
        self.assertEqual(result['res_model'], 'youtube.channel')

    def test_token_expiry_validation(self):
        """
        Test the verification logic for OAuth token expiration dates.
        """
        self.youtube_account.token_expiry_date = datetime.now() - timedelta(hours=1)
        self.assertTrue(self.youtube_account.token_expiry_date <= datetime.now())
        self.youtube_account.token_expiry_date = datetime.now() + timedelta(hours=1)
        self.assertTrue(self.youtube_account.token_expiry_date > datetime.now())
