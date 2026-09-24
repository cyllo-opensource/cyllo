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

class TestSocialInstaAccount(TransactionCase):

    def setUp(self):
        super(TestSocialInstaAccount, self).setUp()
        self.insta_account = self.env['social.insta.account'].create({
            'facebook_insta_page_name': 'Test Insta Page',
            'instagram_access_token': 'dummy_access_token',
            'instagram_page_access_token': 'dummy_page_token',
            'meta_app_number': '123456',
            'meta_app_secret': 'secret',
            'company_id': self.env.company.id
        })

    def test_create_account(self):
        self.assertEqual(self.insta_account.state, 'not connected')
        self.assertFalse(self.insta_account.instagram_connection_authenticated)

    @patch('requests.get')
    def test_action_connect_instagram_success(self, mock_get):
        mock_response_1 = MagicMock()
        mock_response_1.json.return_value = {
            'data': [{'name': 'Test Insta Page', 'id': '987_page_id'}]
        }
        
        mock_response_2 = MagicMock()
        mock_response_2.json.return_value = {
            'instagram_business_account': {'id': 'business_id_123'}
        }
        
        mock_response_3 = MagicMock()
        mock_response_3.json.return_value = {
            'data': [{'id': 'insta_account_id', 'username': 'testuser', 'profile_pic': 'url'}]
        }

        mock_get.side_effect = [mock_response_1, mock_response_2, mock_response_3]

        with patch.object(type(self.insta_account), 'refresh_access_token') as mock_refresh:
            self.insta_account.action_connect_instagram()
            
            self.assertEqual(self.insta_account.facebook_insta_page_number, '987_page_id')
            self.assertEqual(self.insta_account.instagram_business_account_number, 'business_id_123')
            self.assertEqual(self.insta_account.instagram_account_number, 'insta_account_id')
            self.assertEqual(self.insta_account.state, 'connected')
            self.assertTrue(self.insta_account.instagram_connection_authenticated)

    @patch('requests.get')
    def test_refresh_token(self, mock_get):
        mock_response_1 = MagicMock()
        mock_response_1.json.return_value = {'access_token': 'new_long_lived_token'}
        
        mock_response_2 = MagicMock()
        mock_response_2.json.return_value = {'id': 'user_123'}
        
        mock_response_3 = MagicMock()
        mock_response_3.json.return_value = {
            'data': [{'id': '987_page_id', 'access_token': 'new_page_token'}]
        }
        
        self.insta_account.facebook_insta_page_number = '987_page_id'
        mock_get.side_effect = [mock_response_1, mock_response_2, mock_response_3]
        
        self.insta_account.refresh_access_token()
        
        self.assertEqual(self.insta_account.instagram_access_token, 'new_long_lived_token')
        self.assertEqual(self.insta_account.instagram_page_access_token, 'new_page_token')

    def test_disconnect(self):
        self.insta_account.state = 'connected'
        self.insta_account.instagram_connection_authenticated = True
        self.insta_account.renewal_date = fields.Date.today()
        
        self.insta_account.action_disconnect()
        
        self.assertEqual(self.insta_account.state, 'not connected')
        self.assertFalse(self.insta_account.instagram_connection_authenticated)
        self.assertFalse(self.insta_account.renewal_date)
