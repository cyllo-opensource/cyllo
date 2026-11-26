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
import json
from unittest.mock import patch

from odoo.exceptions import ValidationError
from odoo.tests import tagged

from .common import (TEMPLATE_MODULE, WhatsappAutomationCommon, api_error,
                     fake_response)


@tagged('post_install', '-at_install')
class TestWhatsappTemplate(WhatsappAutomationCommon):
    """Tests for the Flows additions to `whatsapp.template`."""

    def setUp(self):
        super().setUp()
        self.flow = self._create_flow(
            'Published Flow', state='published', flow_id='FLOW123')

    def _flow_template(self, **vals):
        values = {
            'template_type': 'flows', 'flows_id': self.flow.id,
            'button_name': 'Open form', 'is_button': False,
        }
        values.update(vals)
        return self._create_template('Flow Template', **values)

    # -- fields -------------------------------------------------------------
    def test_default_type_is_custom(self):
        template = self._create_template()
        self.assertEqual(template.template_type, 'custom')
        self.assertFalse(template.flows_id)
        self.assertFalse(template.action)

    def test_flow_template_creation(self):
        template = self._flow_template(action='create_sale_order')
        self.assertEqual(template.template_type, 'flows')
        self.assertEqual(template.flows_id, self.flow)
        self.assertEqual(template.action, 'create_sale_order')

    def test_flow_domain_only_offers_published_flows(self):
        domain = self.env['whatsapp.template']._fields['flows_id'].domain
        self.assertIn('published', str(domain))

    # -- create() override -------------------------------------------------
    def test_create_links_quotation_template(self):
        so_template = self.env['sale.order.template'].create(
            {'name': 'Quotation Tpl'})
        template = self.env['whatsapp.template'].with_context(
            active_id=so_template.id).create({
                'name': 'Linked', 'template_name': 'linked_tpl',
                'model_id': self.partner_model.id, 'body': 'Hello',
                'action': 'create_sale_order'})
        self.assertEqual(so_template.template_id, template)

    def test_create_without_action_does_not_link(self):
        so_template = self.env['sale.order.template'].create(
            {'name': 'Quotation Tpl'})
        self.env['whatsapp.template'].with_context(
            active_id=so_template.id).create({
                'name': 'Plain', 'template_name': 'plain_tpl',
                'model_id': self.partner_model.id, 'body': 'Hello'})
        self.assertFalse(so_template.template_id)

    def test_create_multi_only_links_matching_vals(self):
        so_template = self.env['sale.order.template'].create(
            {'name': 'Quotation Tpl'})
        templates = self.env['whatsapp.template'].with_context(
            active_id=so_template.id).create([
                {'name': 'A', 'template_name': 'a_tpl', 'body': 'x',
                 'model_id': self.partner_model.id},
                {'name': 'B', 'template_name': 'b_tpl', 'body': 'x',
                 'model_id': self.partner_model.id,
                 'action': 'create_sale_order'},
            ])
        self.assertEqual(so_template.template_id, templates[1])

    # -- submitting the template to Meta ------------------------------------
    @patch(TEMPLATE_MODULE + '.requests.post')
    def test_create_template_approved(self, mock_post):
        mock_post.return_value = fake_response(
            200, {'id': 'tpl_1', 'status': 'APPROVED'})
        template = self._create_template()
        template.action_create_template()
        self.assertEqual(template.template_uid, 'tpl_1')
        self.assertEqual(template.state, 'approved')
        self.assertIn('/test_account/message_templates',
                      mock_post.call_args.args[0])

    @patch(TEMPLATE_MODULE + '.requests.post')
    def test_create_template_rejected(self, mock_post):
        mock_post.return_value = fake_response(
            200, {'id': 'tpl_2', 'status': 'REJECTED'})
        template = self._create_template()
        template.action_create_template()
        self.assertEqual(template.state, 'rejected')
        self.assertTrue(template.is_reason_update)
        self.assertTrue(template.reason)

    @patch(TEMPLATE_MODULE + '.requests.post')
    def test_create_flow_template_sends_flow_button(self, mock_post):
        mock_post.return_value = fake_response(
            200, {'id': 'tpl_3', 'status': 'PENDING'})
        template = self._flow_template()
        template.action_create_template()
        payload = mock_post.call_args.kwargs['json']
        self.assertEqual(payload['name'], template.template_name)
        buttons = [c for c in payload['components']
                   if c['type'] == 'BUTTONS'][0]['buttons']
        self.assertEqual(buttons[0]['type'], 'FLOW')
        self.assertEqual(buttons[0]['flow_id'], 'FLOW123')
        self.assertEqual(buttons[0]['text'], 'Open form')
        self.assertEqual(buttons[0]['flow_action'], 'navigate')
        self.assertEqual(buttons[0]['navigate_screen'], 'SCREEN_ONE')

    @patch(TEMPLATE_MODULE + '.requests.post')
    def test_create_template_includes_footer_and_url_button(self, mock_post):
        mock_post.return_value = fake_response(
            200, {'id': 'tpl_4', 'status': 'PENDING'})
        template = self._create_template(
            footer_text='Thanks', is_button=True, button_name='Visit',
            button_url='https://example.com')
        template.action_create_template()
        types = [c['type'] for c in mock_post.call_args.kwargs['json'][
            'components']]
        self.assertIn('FOOTER', types)
        self.assertIn('BUTTONS', types)

    @patch(TEMPLATE_MODULE + '.requests.post')
    def test_create_template_invalid_token(self, mock_post):
        mock_post.return_value = fake_response(400, api_error(code=190))
        with self.assertRaisesRegex(ValidationError, 'Invalid Access Token'):
            self._create_template().action_create_template()

    @patch(TEMPLATE_MODULE + '.requests.post')
    def test_create_template_invalid_business_account(self, mock_post):
        mock_post.return_value = fake_response(
            400, api_error(code=100, subcode=100))
        with self.assertRaisesRegex(
                ValidationError, 'Invalid Business Account ID'):
            self._create_template().action_create_template()

    @patch(TEMPLATE_MODULE + '.requests.post')
    def test_create_template_generic_error(self, mock_post):
        mock_post.return_value = fake_response(
            400, api_error(message='Template name taken'))
        with self.assertRaisesRegex(ValidationError, 'Template name taken'):
            self._create_template().action_create_template()

    def test_create_template_with_wrong_image_path(self):
        template = self._create_template(
            header_type='image', binary_field_path='name')
        result = template.action_create_template()
        self.assertEqual(result['tag'], 'display_notification')
        self.assertEqual(result['params']['type'], 'warning')

    def test_create_template_requires_account(self):
        self.env.user.token = False
        with self.assertRaises(ValidationError):
            self._create_template().action_create_template()

    # -- sending the template ----------------------------------------------
    def test_send_requires_record(self):
        template = self._create_template(state='approved')
        with self.assertRaisesRegex(ValidationError, 'Record is missed'):
            template.action_send_template(
                self.env['res.partner'], None, self.partner)

    def test_send_requires_approved_template(self):
        template = self._create_template(state='pending')
        with self.assertRaisesRegex(ValidationError, 'approve the template'):
            template.action_send_template(self.partner, None, self.partner)

    @patch(TEMPLATE_MODULE + '.requests.post')
    def test_send_custom_template(self, mock_post):
        mock_post.return_value = fake_response(
            200, {'messages': [{'id': 'wamid.1'}]})
        template = self._create_template(state='approved')
        template.action_send_template(self.partner, None, self.partner)
        payload = mock_post.call_args.kwargs['json']
        self.assertEqual(payload['to'], self.partner.whatsapp_number)
        self.assertEqual(payload['template']['name'], template.template_name)
        self.assertIn('/test_phone/messages', mock_post.call_args.args[0])
        message = self.env['whatsapp.message'].search(
            [('message_uid', '=', 'wamid.1')])
        self.assertEqual(len(message), 1)
        self.assertEqual(message.state, 'sent')
        self.assertTrue(message.is_template)
        self.assertEqual(message.template_id, template)
        self.assertEqual(message.channel_id.partner_id, self.partner)

    @patch(TEMPLATE_MODULE + '.requests.post')
    def test_send_reuses_existing_channel(self, mock_post):
        mock_post.side_effect = [
            fake_response(200, {'messages': [{'id': 'wamid.a'}]}),
            fake_response(200, {'messages': [{'id': 'wamid.b'}]})]
        template = self._create_template(state='approved')
        template.action_send_template(self.partner, None, self.partner)
        template.action_send_template(self.partner, None, self.partner)
        messages = self.env['whatsapp.message'].search(
            [('message_uid', 'in', ['wamid.a', 'wamid.b'])])
        self.assertEqual(len(messages.channel_id), 1)

    @patch(TEMPLATE_MODULE + '.requests.post')
    def test_send_flow_template_embeds_flow_token(self, mock_post):
        mock_post.return_value = fake_response(
            200, {'messages': [{'id': 'wamid.flow'}]})
        template = self._flow_template(state='approved')
        template.action_send_template(self.partner, None, self.partner)
        components = mock_post.call_args.kwargs['json']['template'][
            'components']
        button = [c for c in components if c.get('type') == 'button'][0]
        self.assertEqual(button['sub_type'], 'flow')
        token = json.loads(
            button['parameters'][0]['action']['flow_token'])
        self.assertEqual(token, {'flow_uid': 'FLOW123',
                                 'template_uid': template.id})

    @patch(TEMPLATE_MODULE + '.requests.post')
    def test_send_template_api_error(self, mock_post):
        mock_post.return_value = fake_response(
            400, api_error(message='Recipient not allowed'))
        template = self._create_template(state='approved')
        with self.assertRaisesRegex(ValidationError, 'Recipient not allowed'):
            template.action_send_template(self.partner, None, self.partner)
        self.assertFalse(self.env['whatsapp.message'].search(
            [('template_id', '=', template.id)]))
