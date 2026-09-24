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
from odoo.exceptions import ValidationError
from unittest.mock import MagicMock, patch

class TestWhatsappFlows(TransactionCase):
    """
    Test cases for 'whatsapp.flows' model, covering flow generation,
    screen layouts, response tracking, and API integration.
    """

    def setUp(self):
        """
        Setup test environment for WhatsApp Flows tests.
        """
        super(TestWhatsappFlows, self).setUp()
        self.WhatsappFlows = self.env['whatsapp.flows']
        self.partner = self.env['res.partner'].create({'name': 'Test Partner', 'whatsapp_number': '1234567890'})

    def test_compute_flow_name(self):
        """
        Test the automated computation of a unique technical name for the flow.
        """
        flow = self.WhatsappFlows.create({'name': 'Test Flow'})
        db_uuid = self.env['ir.config_parameter'].sudo().get_param('database.uuid').replace('-', '')
        expected_name = f"test_flow_{db_uuid}"
        self.assertEqual(flow.flow_name, expected_name)

    def test_compute_response_done_count(self):
        """
        Test the computation of completed user responses linked to a flow.
        """
        flow = self.WhatsappFlows.create({'name': 'Test Flow'})
        self.assertEqual(flow.response_done_count, 0)
        
        template = self.env['whatsapp.template'].create({
            'name': 'Test Template',
            'model_id': self.env.ref('base.model_res_partner').id,
            'body': 'Hello',
        })
        
        self.env['flows.user.response'].create({
            'flows_id': flow.id,
            'template_id': template.id,
            'partner_id': self.partner.id,
            'number': '1234567890',
        })
        flow._compute_response_done_count()
        self.assertEqual(flow.response_done_count, 1)

    def test_create_screens(self):
        """
        Test the generation of JSON screen layouts for WhatsApp Flows.
        """
        flow = self.WhatsappFlows.create({'name': 'Test Flow'})
        screen = self.env['whatsapp.flows.screens'].create({
            'name': 'Screen 1',
            'flow_id': flow.id,
            'button_name': 'Next',
        })
        self.env['whatsapp.flows.screen.contents'].create({
            'label': 'Name',
            'content_type': 'text_answer',
            'content_text_answer_type': 'short_answer',
            'screen_id': screen.id,
            'shot_answer_type': 'text',
        })
        
        screens_json = flow.create_screens()
        self.assertEqual(len(screens_json), 1)
        self.assertEqual(screens_json[0]['title'], 'Screen 1')
        children = screens_json[0]['layout']['children'][0]['children']
        text_inputs = [c for c in children if c.get('type') == 'TextInput']
        self.assertEqual(len(text_inputs), 1)
        self.assertEqual(text_inputs[0]['label'], 'Name')

    def test_unlink_restriction(self):
        """
        Test that deleting a published flow is restricted to prevent data loss.
        """
        flow = self.WhatsappFlows.create({'name': 'Test Flow', 'state': 'published'})
        with self.assertRaises(ValidationError):
            flow.unlink()
        
        flow.state = 'draft'
        flow.unlink()

    @patch('requests.post')
    def test_action_confirm_flows(self, mock_post):
        """
        Test the flow confirmation process with mocked external WhatsApp API calls.
        """
        flow = self.WhatsappFlows.create({'name': 'Test Flow'})
        self.env['whatsapp.flows.screens'].create({
            'name': 'Screen 1',
            'flow_id': flow.id,
            'button_name': 'Next',
        })
        
        self.env.user.write({
            'token': 'test_token',
            'account_uid': 'test_acc',
            'phone_uid': 'test_phone',
            'app_uid': 'test_app',
        })
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'id': '12345'}
        mock_post.return_value = mock_response
        
        flow.action_confirm_flows()
        self.assertEqual(flow.flow_id, '12345')
        self.assertEqual(flow.state, 'confirmed')
