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
from unittest.mock import MagicMock, patch

class TestWhatsappTemplate(TransactionCase):
    """
    Test cases for 'whatsapp.template' model enhancements, covering
    Flows template creation, API interaction, and sales order integration.
    """

    def setUp(self):
        """
        Setup test environment for WhatsApp Template tests.
        """
        super(TestWhatsappTemplate, self).setUp()
        self.Template = self.env['whatsapp.template']
        self.Partner = self.env['res.partner']
        self.partner = self.Partner.create({
            'name': 'Test recipient',
            'whatsapp_number': '1234567890',
        })
        self.env.user.write({
            'token': 'test_token',
            'account_uid': 'test_acc',
            'phone_uid': 'test_phone',
            'app_uid': 'test_app',
        })

    def test_whatsapp_template_creation_flows(self):
        """
        Test creating a WhatsApp template linked to a specific Flow.
        """
        flow = self.env['whatsapp.flows'].create({'name': 'Test Flow', 'state': 'published'})
        template = self.Template.create({
            'name': 'Flow Template',
            'template_name': 'flow_template_1',
            'template_type': 'flows',
            'flows_id': flow.id,
            'body': 'Hello',
            'model_id': self.env.ref('base.model_res_partner').id,
        })
        self.assertEqual(template.template_type, 'flows')
        self.assertEqual(template.flows_id, flow)

    @patch('requests.post')
    def test_action_create_template_api(self, mock_post):
        """
        Test the external API synchronization when creating a WhatsApp template.
        """
        template = self.Template.create({
            'name': 'Test Template',
            'template_name': 'test_temp',
            'model_id': self.env.ref('base.model_res_partner').id,
            'body': 'Hello',
        })
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'id': 'temp_123', 'status': 'APPROVED'}
        mock_post.return_value = mock_response
        
        template.action_create_template()
        self.assertEqual(template.template_uid, 'temp_123')
        self.assertEqual(template.state, 'approved')

    @patch('requests.post')
    def test_action_send_template_api(self, mock_post):
        """
        Test the process of sending a templated WhatsApp message via API.
        """
        template = self.Template.create({
            'name': 'Test Template',
            'template_name': 'test_temp',
            'model_id': self.env.ref('base.model_res_partner').id,
            'body': 'Hello',
            'state': 'approved',
        })
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'messages': [{'id': 'msg_123'}]}
        mock_post.return_value = mock_response
        
        with patch.object(self.Template.__class__, '_get_formatted_template_body', return_value='Hello'):
            template.action_send_template(self.partner, None, self.partner)
        
        message = self.env['whatsapp.message'].search([('message_uid', '=', 'msg_123')])
        self.assertTrue(message)
        self.assertEqual(message.state, 'sent')

    def test_create_sale_order_template_association(self):
        """
        Test the automated association of a WhatsApp template with a Sales Order template.
        """
        so_template = self.env['sale.order.template'].create({'name': 'SO Test Template'})
        
        template = self.Template.with_context(active_id=so_template.id).create({
            'name': 'SO WhatsApp Template',
            'template_name': 'so_wh_temp',
            'template_type': 'custom',
            'action': 'create_sale_order',
            'body': 'Hello',
            'model_id': self.env.ref('base.model_res_partner').id,
        })
        
        self.assertEqual(so_template.template_id, template)
