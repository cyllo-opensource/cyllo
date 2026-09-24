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
import base64
from odoo.tests.common import TransactionCase
from unittest.mock import MagicMock, patch

class TestWhatsappMessage(TransactionCase):
    """
    Test cases for 'whatsapp.message' model, covering message lifecycle,
    media attachment processing, and integration with WhatsApp API.
    """

    def setUp(self):
        """
        Setup test environment for WhatsApp Message tests.
        """
        super(TestWhatsappMessage, self).setUp()
        self.Message = self.env['whatsapp.message']
        self.Partner = self.env['res.partner']
        self.partner = self.Partner.create({'name': 'Test Partner', 'whatsapp_number': '1234567890'})

    def test_message_creation(self):
        """
        Test basic creation of a WhatsApp message linked to a channel.
        """
        channel = self.env['whatsapp.channel'].create({
            'name': 'Test Channel',
            'partner_id': self.partner.id,
        })
        message = self.Message.create({
            'channel_id': channel.id,
            'message': 'Hello from Odoo',
            'state': 'sent',
            'message_uid': 'msg_123',
        })
        self.assertEqual(message.channel_id, channel)
        self.assertEqual(message.message, 'Hello from Odoo')
        self.assertEqual(message.state, 'sent')

    @patch('requests.post')
    def test_generate_media_id_mock(self, mock_post):
        """
        Test the retrieval of a media identifier from WhatsApp API for an attachment.
        """
        attachment = self.env['ir.attachment'].create({
            'name': 'test.png',
            'datas': base64.b64encode(b'test content'),
            'mimetype': 'image/png',
        })
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'id': 'media_789'}
        mock_post.return_value = mock_response
        
        token = {'Authorization': 'Bearer test_token'}
        payload = {'messaging_product': 'whatsapp'}
        phone_uid = 'test_phone_uid'
        
        media_id = self.Message.generate_media_id(attachment, token, payload, phone_uid)
        self.assertEqual(media_id, 'media_789')
        self.assertTrue(mock_post.called)

    @patch('requests.post')
    def test_read_receipt_sent(self, mock_post):
        """
        Test that a read receipt is sent to WhatsApp when an unread message is retrieved.
        """
        # Create a user with WhatsApp configuration
        user = self.env['res.users'].create({
            'name': 'Test User',
            'login': 'test_user_whatsapp',
            'token': 'test_token',
            'phone_uid': 'test_phone_uid',
            'account_uid': 'test_account_uid',
            'app_uid': 'test_app_uid',
        })
        
        # Create a channel associated with this user
        channel = self.env['whatsapp.channel'].create({
            'name': 'Test Channel',
            'partner_id': self.partner.id,
            'user_id': user.id,
        })
        
        # Create an incoming unread message
        message = self.Message.create({
            'channel_id': channel.id,
            'message': 'Hello',
            'state': 'received',
            'message_uid': 'msg_123',
            'is_read': False,
            'flag': False,  # Incoming message
        })

        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        # Call get_chat_history, which should trigger read receipt
        self.Message.get_chat_history(channel.id, 10)

        # Verify requests.post was called with correct parameters
        expected_url = f"https://graph.facebook.com/v18.0/{user.phone_uid}/messages"
        expected_headers = {
            'Authorization': f'Bearer {user.token}',
            'Content-Type': 'application/json'
        }
        expected_payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message.message_uid
        }
        
        # Check if called correctly
        mock_post.assert_called_with(expected_url, json=expected_payload, headers=expected_headers)
        
        # Verify message is marked as read in Odoo
        self.assertTrue(message.is_read)
