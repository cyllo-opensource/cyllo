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

class TestWhatsappTemplate(TransactionCase):
    """
    Test cases for 'whatsapp.template' model, covering name generation,
    variable extraction, API synchronization, and text formatting.
    """

    def setUp(self):
        """
        Setup test environment for WhatsApp template configuration tests.
        """
        super(TestWhatsappTemplate, self).setUp()
        self.Template = self.env['whatsapp.template']
        self.env.user.write({
            'token': 'test_token',
            'account_uid': 'test_acc',
            'phone_uid': 'test_phone',
            'app_uid': 'test_app',
        })

    def test_compute_template_name(self):
        """
        Test the automated generation of a unique technical template name.
        """
        template = self.Template.create({
            'name': 'Test Template',
            'model_id': self.env.ref('base.model_res_partner').id,
            'body': 'Hello',
        })
        db_uuid = self.env['ir.config_parameter'].sudo().get_param('database.uuid').replace('-', '')
        expected_name = f"Test_Template_{db_uuid}"
        self.assertEqual(template.template_name, expected_name)

    def test_compute_variable_ids(self):
        """
        Test the automated parsing of variables ({{1}}, {{2}}) from the template body.
        """
        template = self.Template.create({
            'name': 'Test Template',
            'model_id': self.env.ref('base.model_res_partner').id,
            'body': 'Hello {{1}}, welcome to {{2}}!',
        })
        template._compute_variable_ids()
        self.assertEqual(len(template.variable_ids), 2)
        display_names = template.variable_ids.mapped('display_name')
        self.assertIn('body- {1}', display_names)
        self.assertIn('body- {2}', display_names)

    @patch('requests.post')
    def test_action_create_template_api(self, mock_post):
        """
        Test the creation of a WhatsApp template via external API communication.
        """
        template = self.Template.create({
            'name': 'Test Template',
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

    def test_modify_text_to_html(self):
        """
        Test the conversion of WhatsApp-specific Markdown syntax to compliant HTML tags.
        """
        text = "*bold* _italic_ ~strike~ ```code```"
        result = str(self.Template._modify_text_to_html(text))
        self.assertIn("<b>bold</b>", result)
        self.assertIn("<i>italic</i>", result)
        self.assertIn("<s>strike</s>", result)
        self.assertIn("<code>code</code>", result)

    def test_whatsapp_account_details_validation(self):
        """
        Test validation logic for presence of required WhatsApp account credentials.
        """
        template = self.Template.create({
            'name': 'Test Template',
            'model_id': self.env.ref('base.model_res_partner').id,
            'body': 'Hello',
        })
        self.env.user.write({
            'token': False,
            'account_uid': False,
            'phone_uid': False,
            'app_uid': False,
        })
        with self.assertRaises(ValidationError):
            _ = template.get_whatsapp_account_details
            
        self.env.user.write({
            'token': 'test_token',
            'account_uid': 'test_acc',
            'phone_uid': 'test_phone',
            'app_uid': 'test_app',
        })
        
        details = template.get_whatsapp_account_details
        self.assertEqual(details['cloud_token'], 'test_token')
        self.assertEqual(details['phone_uid'], 'test_phone')
