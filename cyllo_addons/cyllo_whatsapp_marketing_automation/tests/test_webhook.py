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
from types import SimpleNamespace
from unittest.mock import patch

from odoo.addons.cyllo_whatsapp_marketing_automation.controllers.main import \
    WebhookMarketing
from odoo.tests import common, tagged

ACCOUNT = 'marketing_account'


@tagged('post_install', '-at_install')
class TestWhatsappMarketingWebhook(common.TransactionCase):
    """Opened / replied tracking driven by the WhatsApp webhook.

    The controller method is called directly with a stand-in `request`.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = cls.env['res.users'].create({
            'name': 'WA Marketing Agent', 'login': 'wa_marketing_agent',
            'account_uid': ACCOUNT,
        })
        cls.partner = cls.env['res.partner'].create({
            'name': 'Tracked Customer', 'whatsapp_number': '15550002222'})
        campaign = cls.env['marketing.campaign'].create({
            'name': 'Tracking Campaign',
            'model_id': cls.env['ir.model']._get('res.partner').id,
        })
        activity = cls.env['marketing.activity'].create({
            'name': 'Tracked', 'campaign_id': campaign.id, 'type': 'whatsapp',
        })
        participant = cls.env['marketing.participant'].create({
            'campaign_id': campaign.id,
            'record': 'res.partner,%s' % cls.partner.id,
        })
        cls.line = cls.env['marketing.activity.line'].create({
            'activity_id': activity.id, 'participant_id': participant.id,
            'state': 'processed', 'whatsapp_message_number': 'wamid.TRACK',
        })
        cls.other = cls.env['marketing.activity.line'].create({
            'activity_id': activity.id, 'participant_id': participant.id,
            'state': 'processed', 'whatsapp_message_number': 'wamid.OTHER',
        })

    def _receive(self, value):
        payload = {'entry': [{'id': ACCOUNT, 'changes': [
            {'field': 'messages', 'value': value}]}]}
        request = SimpleNamespace(env=self.env, get_json_data=lambda: payload)
        with patch('odoo.addons.cyllo_whatsapp_marketing_automation.'
                   'controllers.main.request', request), \
                patch('odoo.addons.cyllo_whatsapp.controllers.main.request',
                      request):
            return WebhookMarketing().webhook_receive_message()

    def _status(self, message_id, status):
        return {'statuses': [{'id': message_id, 'status': status,
                              'recipient_id': '15550002222'}]}

    def _reply(self, context_id=None, message_id='wamid.R1'):
        message = {'id': message_id, 'timestamp': '1700000000',
                   'type': 'text', 'text': {'body': 'Yes please'}}
        if context_id:
            message['context'] = {'id': context_id}
        return {'contacts': [{'wa_id': '15550002222',
                              'profile': {'name': 'Tracked Customer'}}],
                'messages': [message]}

    def test_new_lines_are_neither_opened_nor_replied(self):
        self.assertFalse(self.line.mail_opened)
        self.assertFalse(self.line.mail_replied)

    def test_read_status_marks_the_line_opened(self):
        self._receive(self._status('wamid.TRACK', 'read'))
        self.assertTrue(self.line.mail_opened)
        self.assertFalse(self.line.mail_replied)

    def test_read_status_only_touches_the_matching_line(self):
        self._receive(self._status('wamid.TRACK', 'read'))
        self.assertFalse(self.other.mail_opened)

    def test_other_statuses_do_not_mark_the_line_opened(self):
        for status in ('sent', 'delivered'):
            self._receive(self._status('wamid.TRACK', status))
        self.assertFalse(self.line.mail_opened)

    def test_read_status_of_unknown_message_is_ignored(self):
        self._receive(self._status('wamid.UNKNOWN', 'read'))
        self.assertFalse(self.line.mail_opened)
        self.assertFalse(self.other.mail_opened)

    def test_reply_marks_the_line_replied_and_opened(self):
        self._receive(self._reply(context_id='wamid.TRACK'))
        self.assertTrue(self.line.mail_replied)
        self.assertTrue(self.line.mail_opened)
        self.assertFalse(self.other.mail_replied)

    def test_message_without_context_is_not_a_reply(self):
        self._receive(self._reply(context_id=None))
        self.assertFalse(self.line.mail_replied)
        self.assertFalse(self.other.mail_replied)

    def test_reply_to_unknown_message_is_ignored(self):
        self._receive(self._reply(context_id='wamid.UNKNOWN'))
        self.assertFalse(self.line.mail_replied)

    def test_payload_without_entry_content_is_ignored(self):
        request = SimpleNamespace(
            env=self.env, get_json_data=lambda: {'entry': []})
        with patch('odoo.addons.cyllo_whatsapp_marketing_automation.'
                   'controllers.main.request', request), \
                patch('odoo.addons.cyllo_whatsapp.controllers.main.request',
                      request):
            WebhookMarketing().webhook_receive_message()
        self.assertFalse(self.line.mail_opened)
