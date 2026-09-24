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
from odoo import http
from odoo.http import request
from odoo.addons.cyllo_whatsapp.controllers import main


class WebhookMarketing(main.Webhook):
    """
    Custom webhook handler for marketing activities.
    """

    @http.route('/whatsapp/message/', methods=['POST'], type="json",
                auth="public")
    def webhook_receive_message(self):
        """
        Receive and process incoming webhook messages.

        This method is triggered when a POST request is made to '/whatsapp/message/'.

        Returns:
            dict: Response data.
        """
        res = super(WebhookMarketing, self).webhook_receive_message()
        message = request.get_json_data()
        if 'entry' in message and isinstance(message['entry'], list) and \
                message['entry']:
            entry = message['entry'][0]
            if 'changes' in entry and isinstance(entry['changes'], list) and \
                    entry['changes']:
                change = entry['changes'][0]
                if 'value' in change and 'statuses' in change['value']:
                    statuses = change['value']['statuses']
                    if statuses[0]['status'] == 'read':
                        status_data = statuses[0]
                        context_id = status_data.get('id')
                        if context_id:
                            activity_line = request.env[
                                'marketing.activity.line'].sudo().search([
                                ('whatsapp_message_number', '=', context_id)
                            ])
                            if activity_line:
                                activity_line.sudo().write({
                                    'mail_opened': True,
                                })
                if 'value' in change and 'messages' in change['value']:
                    messages = change['value']['messages']
                    if messages:
                        message_data = messages[0]
                        context_id = message_data.get('context', {}).get('id')
                        if context_id:
                            activity_line = request.env[
                                'marketing.activity.line'].sudo().search([
                                ('whatsapp_message_number', '=', context_id)
                            ])
                            if activity_line:
                                activity_line.sudo().write({
                                    'mail_replied': True,
                                    'mail_opened': True,
                                })
        return res
