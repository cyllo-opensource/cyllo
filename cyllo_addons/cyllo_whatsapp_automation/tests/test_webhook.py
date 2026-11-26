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

from types import SimpleNamespace
from unittest.mock import patch

from odoo.addons.cyllo_whatsapp_automation.controllers.main import \
    WebhookMarketing
from odoo.tests import tagged

from .common import WhatsappAutomationCommon


@tagged('post_install', '-at_install')
class TestFlowWebhook(WhatsappAutomationCommon):
    """Tests for the `/whatsapp/message/` webhook handling flow replies."""

    def setUp(self):
        super().setUp()
        self.wa_user = self.env['res.users'].create({
            'name': 'WhatsApp Agent', 'login': 'wa_agent',
            'account_uid': 'agent_account',
        })
        self.flow = self._flow_with_content()
        self.flow.flow_id = 'FLOW123'
        self.flow.create_screens()  # assigns the input keys of the contents
        self.template = self._create_template(
            template_type='flows', flows_id=self.flow.id)
        self.contents = self.flow.screen_ids.content_ids
        self.name_key = self.contents.filtered(
            lambda c: c.label == 'Name').input_key
        self.colour_key = self.contents.filtered(
            lambda c: c.label == 'Colour').input_key

    def _post(self, flow_answers, flow_token=None, wa_id=None):
        token = flow_token if flow_token is not None else json.dumps(
            {'flow_uid': 'FLOW123', 'template_uid': self.template.id})
        answers = dict(flow_answers, flow_token=token)
        return self._receive({'entry': [{'id': 'agent_account', 'changes': [{
            'field': 'messages',
            'value': {
                'contacts': [{'wa_id': wa_id or self.partner.whatsapp_number,
                              'profile': {'name': self.partner.name}}],
                'messages': [{
                    'id': 'wamid.reply', 'timestamp': '1700000000',
                    'type': 'interactive',
                    'interactive': {'nfm_reply': {
                        'response_json': json.dumps(answers)}},
                }],
            }}]}]})

    def _receive(self, payload):
        fake_request = SimpleNamespace(
            env=self.env, get_json_data=lambda: payload)
        with patch('odoo.addons.cyllo_whatsapp_automation.controllers.main.'
                   'request', fake_request), \
                patch('odoo.addons.cyllo_whatsapp.controllers.main.request',
                      fake_request):
            return WebhookMarketing().webhook_receive_message()

    def _responses(self):
        return self.env['flows.user.response'].search(
            [('flows_id', '=', self.flow.id)])

    def test_flow_reply_is_stored(self):
        self._post({self.name_key: 'John', self.colour_key: 'Red'})
        response = self._responses()
        self.assertEqual(len(response), 1)
        self.assertEqual(response.partner_id, self.partner)
        self.assertEqual(response.template_id, self.template)
        self.assertEqual(response.number, self.partner.whatsapp_number)
        self.assertEqual(response.state, 'draft')
        lines = {l.field_label: l for l in response.flows_user_response_line_ids}
        self.assertEqual(set(lines), {'Name', 'Colour'})
        self.assertEqual(lines['Name'].user_input, 'John')
        self.assertEqual(lines['Colour'].user_input, 'Red')
        self.assertEqual(lines['Name'].response_key, self.name_key)
        self.assertEqual(lines['Name'].screen_id.name, 'Details')

    def test_unanswered_fields_are_skipped(self):
        self._post({self.name_key: 'John'})
        lines = self._responses().flows_user_response_line_ids
        self.assertEqual(lines.mapped('field_label'), ['Name'])

    def test_reply_without_answers_creates_nothing(self):
        self._post({})
        self.assertFalse(self._responses())

    def test_unknown_flow_is_ignored(self):
        token = json.dumps({'flow_uid': 'OTHER', 'template_uid': self.template.id})
        self._post({self.name_key: 'John'}, flow_token=token)
        self.assertFalse(self._responses())

    def test_unknown_sender_is_stored_without_partner(self):
        self._post({self.name_key: 'John'}, wa_id='911111111111')
        response = self._responses()
        self.assertEqual(len(response), 1)
        self.assertFalse(response.partner_id)
        self.assertEqual(response.number, '911111111111')

    def test_text_message_is_not_treated_as_flow_reply(self):
        self._receive({'entry': [{'id': 'agent_account', 'changes': [{
            'field': 'messages',
            'value': {
                'contacts': [{'wa_id': self.partner.whatsapp_number,
                              'profile': {'name': self.partner.name}}],
                'messages': [{'id': 'wamid.text', 'timestamp': '1',
                              'type': 'text', 'text': {'body': 'hello'}}],
            }}]}]})
        self.assertFalse(self._responses())
        message = self.env['whatsapp.message'].search(
            [('message_uid', '=', 'wamid.text')])
        self.assertEqual(message.message, 'hello')

    def test_malformed_flow_token_is_ignored(self):
        for token in ('not json', '{"flow_uid": "FLOW123"}',
                      "__import__('os').getcwd()", '[1, 2]'):
            self._post({self.name_key: 'John'}, flow_token=token)
        self.assertFalse(self._responses())
