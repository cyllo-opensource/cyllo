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
from odoo.addons.cyllo_sms_gateway.tests.common import TestCylloSmsGateway
from odoo.tests.common import BlockedRequest

class TestSendSms(TestCylloSmsGateway):
    """
    Test cases for 'send.sms' wizard, covering recipient selection, 
    SMS transmission attempts, and history logging.
    """

    def test_onchange_partner_ids(self):
        """
        Test the automated update of the mobile number when partners are selected.
        """
        self.send_sms._onchange_partner_ids()
        self.assertEqual('+9876543210', self.send_sms.sms_to)

    def test_action_send_sms(self):
        """
        Test the SMS sending action, ensuring it handles API connectivity and 
        request blocking appropriately.
        """
        self.send_sms.sms_id.twilio_account_sid = "TEST_SID"
        self.send_sms.sms_id.twilio_auth_token = "TEST_TOKEN"
        self.send_sms.sms_id.twilio_phone_number = "+911234567890"

        action = self.send_sms.action_send_sms()

        self.assertEqual(action['type'], 'ir.actions.client')
        self.assertEqual(action['tag'], 'display_notification')
        self.assertIsInstance(
            action['params']['message'],
            BlockedRequest
        )

    def test_create_sms_history(self):
        """
        Test the verification of SMS history entry creation after a send attempt.
        """
        self.send_sms.create_sms_history('Success', sid='TEST_SID_001')
        sms_history = self.env['sms.history'].search([
            ('user_id', '=', self.env.user.id),
            ('sms_gateway_id', '=', self.send_sms.sms_id.id),
            ('sms_mobile', '=', self.send_sms.sms_to),
            ('sms_text', '=', self.send_sms.text),
            ('sms_status', '=', 'Success'),
        ])
        self.assertTrue(sms_history, "SMS history record should be created")
