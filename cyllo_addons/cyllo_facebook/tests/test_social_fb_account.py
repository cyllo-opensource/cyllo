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
from unittest.mock import patch, MagicMock
from odoo import fields


class TestSocialFbAccount(TransactionCase):

    def setUp(self):
        super().setUp()
        self.fb_account = self.env['social.fb.account'].create({
            'facebook_page_name': 'Test Page',
            'facebook_access_token': 'dummy_access_token',
            'facebook_user_access_token': 'dummy_user_access_token',
            'meta_app_number': '123456',
            'meta_app_secret': 'secret',
            'company_id': self.env.company.id,
        })

    def test_create_account(self):
        """Account starts disconnected"""
        self.assertEqual(self.fb_account.state, 'not connected')
        self.assertFalse(self.fb_account.facebook_connection_authenticated)

    @patch('requests.get')
    def test_action_connect_success(self, mock_get):
        """Successful page connection"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'data': [{'name': 'Test Page', 'id': '987654321'}]
        }
        mock_get.return_value = mock_response

        with patch.object(
            type(self.fb_account),
            'refresh_access_token'
        ) as mock_refresh:

            self.fb_account.action_connect()

            self.assertEqual(self.fb_account.facebook_page_number, '987654321')
            self.assertEqual(self.fb_account.state, 'connected')
            self.assertTrue(self.fb_account.facebook_connection_authenticated)

            self.assertGreaterEqual(mock_refresh.call_count, 1)

    @patch('requests.get')
    def test_action_connect_failure_error(self, mock_get):
        """API error returns warning"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'error': {'message': 'Invalid token'}
        }
        mock_get.return_value = mock_response

        result = self.fb_account.action_connect()

        self.assertEqual(result['params']['type'], 'warning')
        self.assertIn('Invalid token', result['params']['message'])

    @patch('requests.get')
    def test_action_connect_page_not_found(self, mock_get):
        """Page name not found"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'data': [{'name': 'Other Page', 'id': '11111'}]
        }
        mock_get.return_value = mock_response

        result = self.fb_account.action_connect()

        self.assertEqual(result['params']['type'], 'warning')
        self.assertIn('Page not found', result['params']['message'])

    @patch('requests.get')
    def test_refresh_token(self, mock_get):
        """Token refresh flow"""
        mock_response_1 = MagicMock()
        mock_response_1.json.return_value = {'access_token': 'new_long_lived_token'}

        mock_response_2 = MagicMock()
        mock_response_2.json.return_value = {'id': 'user_123'}

        mock_response_3 = MagicMock()
        mock_response_3.json.return_value = {
            'data': [{'id': '987654321', 'access_token': 'new_page_token'}]
        }

        self.fb_account.facebook_page_number = '987654321'
        mock_get.side_effect = [mock_response_1, mock_response_2, mock_response_3]

        self.fb_account.refresh_access_token()

        self.assertEqual(
            self.fb_account.facebook_user_access_token,
            'new_long_lived_token'
        )
        self.assertEqual(
            self.fb_account.facebook_access_token,
            'new_page_token'
        )
        self.assertTrue(self.fb_account.expiry_date)

    def test_disconnect(self):
        """Disconnect resets state"""
        self.fb_account.state = 'connected'
        self.fb_account.facebook_connection_authenticated = True

        self.fb_account.action_disconnect()

        self.assertEqual(self.fb_account.state, 'not connected')
        self.assertFalse(self.fb_account.facebook_connection_authenticated)
