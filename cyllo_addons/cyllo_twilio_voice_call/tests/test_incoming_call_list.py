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

class TestIncomingCallList(TransactionCase):

    def setUp(self):
        super(TestIncomingCallList, self).setUp()
        self.IncomingCall = self.env['incoming.call.list']
        self.company = self.env.user.company_id
        self.partner = self.env['res.partner'].create({
            'name': 'Test Partner',
            'mobile': '+1234567890',
        })
        
        # Setup Config Parameters
        self.env['ir.config_parameter'].sudo().set_param('cyllo_twilio_voice_call.account_sid', 'AC_TEST')
        self.env['ir.config_parameter'].sudo().set_param('cyllo_twilio_voice_call.auth_token', 'TOKEN_TEST')
        self.env['ir.config_parameter'].sudo().set_param('cyllo_twilio_voice_call.from_number', '+1987654321')

    def test_create_sequence(self):
        """Test that the sequence is generated on creation"""
        record = self.IncomingCall.create({
            'from_number': '+1112223333',
        })
        self.assertTrue(record.reference)
        self.assertNotEqual(record.reference, 'New')
        self.assertTrue(record.reference.startswith('New') is False) # Assuming sequence is set up

    @patch('odoo.addons.cyllo_twilio_voice_call.models.incoming_call_list.Client')
    def test_action_incoming_call(self, MockClient):
        """Test action_incoming_call creating a record"""
        # Setup Mock
        mock_call = MagicMock()
        mock_call.duration = "10"
        mock_call.status = "completed"
        
        MockClient.return_value.calls.return_value.fetch.return_value = mock_call
        dummy_rec = self.IncomingCall.create({})
        dummy_rec.action_incoming_call('+1555555555', 'CA_TEST_SID')

        # Check if record was created
        created_call = self.IncomingCall.search([('call_sid', '=', 'CA_TEST_SID')], limit=1)
        self.assertTrue(created_call)
        self.assertEqual(created_call.from_number, '+1555555555')
        self.assertEqual(created_call.status, 'completed')

    @patch('odoo.addons.cyllo_twilio_voice_call.models.incoming_call_list.Client')
    def test_action_incoming_from_partner(self, MockClient):
        """Test incoming call from a known partner"""
        mock_call = MagicMock()
        mock_call.duration = "20"
        mock_call.status = "in-progress"
        MockClient.return_value.calls.return_value.fetch.return_value = mock_call

        dummy_rec = self.IncomingCall.create({})
        dummy_rec.action_incoming_from_partner('+1234567890', 'CA_PARTNER_SID', self.partner.id)

        created_call = self.IncomingCall.search([('call_sid', '=', 'CA_PARTNER_SID')], limit=1)
        self.assertTrue(created_call)
        self.assertEqual(created_call.partner_id, self.partner)
        self.assertEqual(created_call.from_number, '+1234567890')

    @patch('odoo.addons.cyllo_twilio_voice_call.models.incoming_call_list.Client')
    def test_action_hanging_call(self, MockClient):
        """Test updating record on hangup"""
        # First create a record representing active call
        active_rec = self.IncomingCall.create({
            'call_sid': 'CA_ACTIVE_SID',
            'status': 'in-progress'
        })
        
        mock_call = MagicMock()
        mock_call.duration = "125" # 2 minutes 5 seconds
        mock_call.status = "completed"
        MockClient.return_value.calls.return_value.fetch.return_value = mock_call
        
        # calling method
        active_rec.action_hanging_call('+111', 'CA_ACTIVE_SID')
        
        active_rec.invalidate_model()
        self.assertEqual(active_rec.status, 'completed')
        self.assertEqual(active_rec.duration, '02:05')
        self.assertTrue(active_rec.end_time)

    def test_action_play_recording(self):
        """Test play recording action"""
        record = self.IncomingCall.create({
            'record_sid': 'http://api.twilio.com/recordings/RE123',
        })
        action = record.action_play_recording()
        self.assertEqual(action['type'], 'ir.actions.act_url')
        self.assertEqual(action['url'], 'http://api.twilio.com/recordings/RE123')
        
        record.record_sid = False
        self.assertFalse(record.action_play_recording())
