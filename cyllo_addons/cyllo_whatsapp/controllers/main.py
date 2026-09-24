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
import base64
import logging

from http import HTTPStatus

import requests
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class Webhook(http.Controller):
    """Controller for handling WhatsApp webhooks in a Cyllo module."""

    @http.route('/check_model/whatsapp', type="json", auth="public")
    def check_model_exist(self):
        """Check whether model exist."""
        model = bool(request.env['ir.model'].sudo().search_count(
            [('model', '=', 'whatsapp.channel')]))
        return model

    @http.route('/whatsapp/message/', methods=['POST'], type="json",
                auth="public")
    def webhook_receive_message(self):
        """
        Handle incoming messages in a WhatsApp webhook.

        This method processes incoming messages from the WhatsApp webhook and
        creates corresponding records in the Odoo database. It handles text
        messages, as well as media messages like images,
        audio, and documents.

        Parameters:
            - None

        Returns:
            - None

        The function processes the JSON data received in the POST request and
        creates records in the 'whatsapp.message' model for each incoming
        message. It extracts information such as message type, text content,
        and media attachments. It also creates or updates related records in
        the 'res.partner' and 'whatsapp.channel' models based on the sender's
        and recipient's information.
        """
        data = request.get_json_data()
        for entry in data['entry']:
            user = request.env['res.users'].sudo().search(
                [('account_uid', '=', entry['id'])], limit=1)
            if not user:
                _logger.warning(
                    "This account is not configured for any user: %s ", data)
            else:
                for changes in entry.get('changes', []):
                    value = changes['value']
                    if changes['field'] == 'messages':
                        if value.get('messages'):
                            message = \
                                data['entry'][0]['changes'][0]['value']['messages'][
                                    0]
                            message_values = {'flag': False,
                                              'state': 'received',
                                              'message_uid': message['id']}
                            if message['type'] == 'text':
                                message_values['message'] = message['text'][
                                    'body']
                                message_values['message_type'] = message['type']
                            elif message['type'] in ['image', 'audio',
                                                     'document', 'video',
                                                     'sticker']:
                                message_type = message['type']
                                media_id = message[message_type]['id']
                                response = self._extract_binary_data(media_id,
                                                                     user)
                                attachment_values = {
                                    'mimetype': message[message_type][
                                        'mime_type'],
                                    'datas': base64.b64encode(response.content)}
                                if message_type == 'image':
                                    caption = message[message_type].get(
                                        'caption', None)
                                    message_values['message'] = caption
                                    message_values['image'] = base64.b64encode(
                                        response.content)
                                    file_name = 'IMG-WA-' + message[
                                        'timestamp'] + '.png'
                                    attachment_values['name'] = file_name
                                elif message_type == 'sticker':
                                    message_values[
                                        'sticker'] = base64.b64encode(
                                        response.content).decode()
                                    file_name = 'IMG-ST-' + message[
                                        'timestamp'] + '.webp'
                                    attachment_values['name'] = file_name
                                elif message_type == 'audio':
                                    file_name = 'AUD-WA-' + message[
                                        'timestamp'] + '.opus'
                                    attachment_values['name'] = file_name
                                elif message_type == 'video':
                                    file_name = 'VID-WA-' + message[
                                        'timestamp'] + '.mp4'
                                    attachment_values['name'] = file_name
                                else:
                                    caption = message[message_type].get(
                                        'caption', None)
                                    message_values['message'] = caption
                                    attachment_values['name'] = \
                                        message[message_type]['filename']
                                attachment = request.env[
                                    'ir.attachment'].sudo().create(
                                    attachment_values)
                                message_values['attachment_id'] = attachment.id
                                message_values['message_type'] = message['type']
                                if message.get('audio', {}).get('voice'):
                                    message_values['is_voice'] = True
                                else:
                                    message_values['is_voice'] = False
                            else:
                                _logger.warning(
                                    "Unsupported whatsapp message type: %s",
                                    message['type'])
                                continue
                            if value.get('contacts'):
                                profile = \
                                    data['entry'][0]['changes'][0]['value'][
                                        'contacts'][0]
                                number = profile['wa_id']
                                partner = request.env[
                                    'res.partner'].sudo().search(
                                    [('whatsapp_number', '=', number)])
                                if not partner:
                                    partner = request.env[
                                        'res.partner'].sudo().create(
                                        {'name': profile['profile']['name'],
                                         'user_id': user.id,
                                         'whatsapp_number': profile['wa_id']})
                                channel = request.env[
                                    'whatsapp.channel'].sudo().search(
                                    [('partner_id', '=', partner.id),
                                     ('user_id', '=', user.id)])
                                if not channel:
                                    channel = request.env[
                                        'whatsapp.channel'].sudo().create(
                                        {'sender_id': user.partner_id.id,
                                         'partner_id': partner.id,
                                         'user_id': user.id,
                                         'name': partner.name})
                                message_values['channel_id'] = channel.id
                            received_message = request.env[
                                'whatsapp.message'].sudo().create(
                                message_values)
                            channel.write({
                                'last_message': received_message.message,
                                'last_messenger': channel.name,
                            })
                            channel = "WHATSAPP-CHANNEL"
                            message = {
                                "channel": channel,
                                "message": received_message.read(),
                            }
                            request.env["bus.bus"]._sendone(channel,
                                                            "notification",
                                                            message)
                    if value.get('statuses'):
                        for record in value.get('statuses'):
                            message = request.env[
                                'whatsapp.message'].sudo().search(
                                [('message_uid', 'ilike', record.get('id'))])
                            message.state = record.get('status')
                            if record.get('status') == 'read':
                                message.is_read = True
                            request.env["bus.bus"]._sendone("WHATSAPP-CHANNEL",
                                                            "STATE-UPDATE",
                                                            message)
                if value.get('message_template_id'):
                    wa_template = self._get_wa_template(
                        value['message_template_id'])
                    self._update_template_from_respons(wa_template,
                                                       changes['field'], value)

    @http.route(['/whatsapp/message', '/whatsapp/message/'], methods=['GET'],
                type="http", auth="public", csrf=False)
    def receive_message(self, **kwargs):
        """
        Handle incoming messages from WhatsApp webhook.
        :param kwargs: Keyword arguments containing information from the request.
        :return: Response based on the validation and subscription status.
        """
        mode = kwargs.get("hub.mode")
        challenge = kwargs.get("hub.challenge")
        token = kwargs.get("hub.verify_token")
        verify_token = request.env['ir.config_parameter'].sudo().get_param(
            'res_users.whatsapp_return_token'
        )
        if mode == "subscribe" and token == verify_token:
            response = request.make_response(challenge)
            response.status_code = HTTPStatus.OK
            return response
        return http.Response("Invalid Verify Token",
                             status=HTTPStatus.FORBIDDEN)

    def _extract_binary_data(self, media_id, user):
        """ Retrieve binary data associated with a media ID from the Facebook
        Graph API.

        Parameters:
            - media_id (str): The ID of the media for which binary data is to be
             retrieved.
            - user (res.users): The user associated with the authentication token.

        Returns:
            - requests.Response or None: If successful, a `requests.Response`
             object containing the binary data. If unsuccessful or an error
             occurs, returns None.
        """

        headers = {'Authorization': f'Bearer {user.token}'}
        url = f'https://graph.facebook.com/v18.0/{media_id}/'
        response = requests.get(url, headers=headers)
        data = response.json()
        media_url = data.get('url', '')
        if media_url:
            response = requests.get(media_url, headers=headers)
            return response
        return None

    def _get_wa_template(self, message_template_id):
        """ Search the template corresponds to response template_uid """
        return request.env['whatsapp.template'].sudo().search(
            [('template_uid', '=', message_template_id)])

    def _update_template_from_respons(self, wa_template, field, value):
        """
         Update the given `wa_template` based on the specified `field` and `value`.

         Parameters:
         - wa_template (Template): The template to be updated.
         - field (str): The field indicating the type of update (e.g., 'message_template_status_update').
         - value (dict): The data containing the information for the update.

         Returns:
         None"""
        if wa_template:
            if field == 'message_template_status_update':
                wa_template.state = value['event'].lower()
                if wa_template.state == 'rejected':
                    wa_template.is_reason_update = True
                    wa_template.reason = value['reason']
            if field == 'message_template_quality_update':
                wa_template.quality = value['new_quality_score'].lower()
