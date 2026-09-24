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
from odoo.tests.common import TransactionCase

class TestResConfigSettings(TransactionCase):

    def setUp(self):
        super(TestResConfigSettings, self).setUp()
        self.ResConfig = self.env['res.config.settings']
        self.config = self.ResConfig.create({})

    def test_default_twilio_user_identity(self):
        """Test default twilio user identity generation"""
        # Ensure user login has some non-word characters to test sanitization
        self.env.user.login = "admin@example.com"
        expected_identity = f"user_{self.env.user.id}_adminexamplecom"
        
        # We need to call the default method directly or through creating a new wizard
        identity = self.config._default_twilio_user_identity()
        self.assertEqual(identity, expected_identity)
        # Verify it populates on new record creation
        # First remove any existing param that might be read by default_get
        self.env['ir.config_parameter'].sudo().set_param('cyllo_twilio_voice_call.twilio_user_identity', False)
        new_config = self.ResConfig.create({})
        self.assertEqual(new_config.twilio_user_identity, expected_identity)

    def test_set_and_get_params(self):
        """Test setting and getting config parameters"""
        self.config.account_sid = 'AC123456'
        self.config.auth_token = 'token123'
        self.config.set_values()

        # Check if values are stored in ir.config_parameter
        get_param = self.env['ir.config_parameter'].sudo().get_param
        self.assertEqual(get_param('cyllo_twilio_voice_call.account_sid'), 'AC123456')
        self.assertEqual(get_param('cyllo_twilio_voice_call.auth_token'), 'token123')

    @patch('odoo.addons.cyllo_twilio_voice_call.models.res_config_settings.Client')
    def test_twilio_connection_success(self, MockClient):
        """Test successful interaction with test_twilio_connection"""
        # Setup mock behavior
        mock_client_instance = MockClient.return_value
        
        # 1. API Key/Secret success
        mock_client_instance.applications.return_value.fetch.return_value = MagicMock(sid='AP123')
        
        # 2. Account SID/Token success
        mock_client_instance.verify.v2.services.create.return_value = MagicMock(sid='VA123')
        
        # 3. Phone Number Validation success
        mock_client_instance.lookups.v1.phone_numbers.return_value.fetch.return_value = MagicMock(phone_number='+1234567890')

        self.config.account_sid = 'AC_TEST'
        self.config.auth_token = 'TOKEN'
        self.config.api_key = 'KEY'
        self.config.api_secret = 'SECRET'
        self.config.outgoing_application_sid = 'AP_TEST'
        self.config.from_number = '+1234567890'

        result = self.config.test_twilio_connection()
        
        self.assertEqual(result['tag'], 'display_notification')
        self.assertEqual(result['params']['type'], 'success')
        self.assertIn("All checks passed", result['params']['message'])

    @patch('odoo.addons.cyllo_twilio_voice_call.models.res_config_settings.Client')
    def test_twilio_connection_failure(self, MockClient):
        """Test failure scenarios"""
        # Simulate exception on client init or call
        MockClient.side_effect = Exception("Connection Failed")
        
        result = self.config.test_twilio_connection()
        
        self.assertEqual(result['tag'], 'display_notification')
        self.assertEqual(result['params']['type'], 'danger')
        self.assertIn("Unexpected error", result['params']['message'])
