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

class TestSmsGatewayConfig(TestCylloSmsGateway):
    """
    Test cases for 'sms.gateway.config' model, covering connectivity tests 
    and activation/deactivation workflows.
    """

    def test_action_test_connection(self):
        """
        Test the action that triggers a connection test wizard.
        """
        action = self.sms_gateway.action_test_connection()
        self.assertEqual(action['name'], 'Send SMS')
        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(action['res_model'], 'send.sms')
        self.assertEqual(action['context'], {'default_sms_id': self.sms_gateway.id})
        self.assertEqual(action['view_mode'], 'form')
        self.assertEqual(action['target'], 'new')

    def test_action_activate(self):
        """
        Test the activation of an SMS gateway and its association with the company.
        """
        self.sms_gateway.action_activate()
        self.assertTrue(self.sms_gateway.is_active)
        self.assertEqual(self.sms_gateway.company_id, self.env.company)

    def test_action_deactivate(self):
        """
        Test the deactivation process, ensuring credentials and company associations are cleared.
        """
        self.sms_gateway.action_deactivate()

        self.assertFalse(self.sms_gateway.is_active)
        self.assertFalse(self.sms_gateway.company_id)
        self.assertEqual(self.sms_gateway.twilio_account_sid, "")
        self.assertEqual(self.sms_gateway.twilio_auth_token, "")
        self.assertEqual(self.sms_gateway.twilio_phone_number, "")
