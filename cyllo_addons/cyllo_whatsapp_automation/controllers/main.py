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
import json


class WebhookMarketing(main.Webhook):
    """
    Webhook controller for handling incoming WhatsApp messages and processing
    user interactions with WhatsApp flow templates.

    This class extends the `Webhook` class to add custom functionality for
    processing interactive messages, extracting flow responses, and storing
    them in the system.
    """

    @http.route('/whatsapp/message/', methods=['POST'], type="json",
                auth="public")
    def webhook_receive_message(self):
        """
        Handle incoming WhatsApp messages and process user responses in flows.

        This method is triggered when a message is received from WhatsApp. It
        processes interactive messages, extracts flow responses, and stores
        the relevant data in the system, including user responses and
        associated flow details.

        Returns:
            dict: The response returned by the parent class's
            `webhook_receive_message` method.
        """
        res = super(WebhookMarketing, self).webhook_receive_message()
        data = request.get_json_data()
        entry = data.get('entry', [])[0]
        changes = entry.get('changes', [])
        if not changes:
            return res
        for change in changes:
            if change.get('field') == 'messages' and change.get('value', {}).get('messages'):
                message = change['value']['messages'][0]
                if message.get('type') == 'interactive':
                    profile = entry['changes'][0]['value']['contacts'][0]
                    partner = request.env['res.partner'].sudo().search(
                        [('whatsapp_number', '=', profile['wa_id'])]
                    )
                    flow_response = json.loads(message['interactive']['nfm_reply']['response_json'])
                    flow_token = eval(flow_response['flow_token'])['flow_uid']
                    template_id = eval(flow_response['flow_token'])['template_uid']
                    flow = request.env['whatsapp.flows'].sudo().search([('flow_id', '=', flow_token)])
                    if flow:
                        user_responses = [
                            {
                                'field_label': content.label,
                                'screen_id': content.screen_id.id,
                                'product_id': content.product_id.id,
                                'user_input': flow_response.get(
                                    content.input_key),
                                'response_key': content.input_key
                            }
                            for content in flow.mapped('screen_ids.content_ids')
                            if content.input_key and flow_response.get(
                                content.input_key)
                        ]
                        if user_responses:
                            user_response = request.env[
                                'flows.user.response'].sudo().create({
                                'flows_id': flow.id,
                                'template_id': template_id,
                                'partner_id': partner.id if partner else False,
                                'number': profile['wa_id'],
                                'company_id': request.env.company.id,
                                'json_format': flow_response,
                            })
                            response_lines = [
                                {'response_id': user_response.id, **item}
                                for item in user_responses
                            ]
                            if response_lines:
                                request.env[
                                    'flows.user.response.line'].sudo().create(
                                    response_lines)
        return res
