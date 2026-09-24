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

class TestOutGoingCallList(TransactionCase):

    def setUp(self):
        super(TestOutGoingCallList, self).setUp()
        self.OutGoingCall = self.env['out.going.call.list']
        self.partner = self.env['res.partner'].create({
            'name': 'Test Partner Out',
            'mobile': '+9998887777',
        })
        
        # Setup Config Parameters
        self.env['ir.config_parameter'].sudo().set_param('cyllo_twilio_voice_call.account_sid', 'AC_TEST_OUT')
        self.env['ir.config_parameter'].sudo().set_param('cyllo_twilio_voice_call.auth_token', 'TOKEN_TEST_OUT')
        self.env['ir.config_parameter'].sudo().set_param('cyllo_twilio_voice_call.from_number', '+1555000000')

    def test_create_sequence(self):
        """Test sequence generation"""
        record = self.OutGoingCall.create({
            'to_number': '+9998887777',
        })
        self.assertTrue(record.reference)
        self.assertNotEqual(record.reference, 'New')

    @patch('odoo.addons.cyllo_twilio_voice_call.models.out_going_call_list.Client')
    def test_action_call(self, MockClient):
        """Test action_call with partner"""
        mock_call = MagicMock()
        mock_call.duration = "15"
        MockClient.return_value.calls.return_value.fetch.return_value = mock_call

        dummy_rec = self.OutGoingCall.create({})
        dummy_rec.action_call('+9998887777', 'CA_OUT_SID', self.partner.id)

        created = self.OutGoingCall.search([('call_sid', '=', 'CA_OUT_SID')], limit=1)
        self.assertTrue(created)
        self.assertEqual(created.partner_id, self.partner)
        self.assertEqual(created.to_number, '+9998887777')

    @patch('odoo.addons.cyllo_twilio_voice_call.models.out_going_call_list.Client')
    def test_action_making_call(self, MockClient):
        """Test action_making_call without partner"""
        mock_call = MagicMock()
        mock_call.duration = "5"
        MockClient.return_value.calls.return_value.fetch.return_value = mock_call

        dummy_rec = self.OutGoingCall.create({})
        dummy_rec.action_making_call('+1112223333', 'CA_MAKE_SID')

        created = self.OutGoingCall.search([('call_sid', '=', 'CA_MAKE_SID')], limit=1)
        self.assertTrue(created)
        self.assertEqual(created.to_number, '+1112223333')
        self.assertFalse(created.partner_id)

    @patch('odoo.addons.cyllo_twilio_voice_call.models.out_going_call_list.Client')
    def test_action_cancel_create_new(self, MockClient):
        """Test action_cancel creating a new record (if not found by SID)"""
        # If no local record exists with that SID, it creates one
        mock_call = MagicMock()
        MockClient.return_value.calls.return_value.fetch.return_value = mock_call

        dummy_rec = self.OutGoingCall.create({})
        result = dummy_rec.action_cancel('+9998887777', 'CA_CANCEL_NEW_SID') # Uses partner number

        created = self.OutGoingCall.search([('call_sid', '=', 'CA_CANCEL_NEW_SID')], limit=1)
        self.assertTrue(created)
        # Check logic for partner matching
        self.assertEqual(created.partner_id, self.partner)
        self.assertEqual(result, "Call details updated successfully.")

    @patch('odoo.addons.cyllo_twilio_voice_call.models.out_going_call_list.Client')
    def test_action_cancel_update_existing(self, MockClient):
        """Test action_cancel updating existing record"""
        existing = self.OutGoingCall.create({
            'call_sid': 'CA_EXISTING_SID',
            'status': 'in-progress'
        })
        
        mock_call = MagicMock()
        MockClient.return_value.calls.return_value.fetch.return_value = mock_call
        
        # Call cancel logic
        existing.action_cancel('+9998887777', 'CA_EXISTING_SID')
        
        existing.invalidate_model()
        self.assertTrue(existing.end_time)
        self.assertEqual(existing.partner_id, self.partner) # Should update partner based on number

    def test_action_play_recording(self):
        """Test play recording"""
        record = self.OutGoingCall.create({
            'record_sid': 'http://example.com/rec',
        })
        res = record.action_play_recording()
        self.assertEqual(res['url'], 'http://example.com/rec')
