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
import hashlib
import hmac
import logging

import requests
from http import HTTPStatus
from odoo import http
from odoo.fields import Datetime
from odoo.http import request
from werkzeug.exceptions import Forbidden
from odoo import _

_logger = logging.getLogger(__name__)


class WebHook(http.Controller):
    """Controller handling Instagram webhook interactions."""

    @http.route('/instagram/webhook/', methods=['GET'], type="http",
                auth="public", csrf=False)
    def receive_message(self, **kwargs):
        """Handle GET requests to the Instagram webhook."""
        token = kwargs.get('hub.verify_token')
        mode = kwargs.get('hub.mode')
        challenge = kwargs.get('hub.challenge')
        if kwargs:
            if not (token and mode and challenge):
                return Forbidden()
            if mode == 'subscribe':
                response = request.make_response(challenge)
                response.status_code = HTTPStatus.OK
                return response
            response = request.make_response({})
            response.status_code = HTTPStatus.FORBIDDEN
            return response

    def _verify_signature(self):
        """ Same Meta signature scheme as Facebook's webhook - see
        cyllo_facebook/controllers/main.py's _verify_signature for the full
        rationale. Instagram accounts keep their own meta_app_secret, so
        checked against those instead of social.fb.account's. """
        signature_header = request.httprequest.headers.get('X-Hub-Signature-256', '')
        if not signature_header.startswith('sha256='):
            return False
        provided = signature_header.split('=', 1)[1]
        raw_body = request.httprequest.get_data()
        secrets = request.env['social.insta.account'].sudo().search(
            [('meta_app_secret', '!=', False)]).mapped('meta_app_secret')
        for secret in set(secrets):
            expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
            if hmac.compare_digest(expected, provided):
                return True
        return False

    @http.route('/instagram/webhook/', methods=['POST'], type="json",
                auth="public")
    def get_message_data(self):
        """Handle POST requests containing Instagram message data."""
        if not self._verify_signature():
            _logger.warning("Instagram webhook: rejected POST with invalid/missing signature.")
            raise Forbidden()
        try:
            data = request.get_json_data()
            if not data['entry'][0].get('messaging')[0].get(
                        'message').get('is_echo'):
                recipient_id = data['entry'][0].get('id')
                accounts = request.env['social.insta.account'].sudo().search(
                    ['|', ('instagram_business_account_number', '=',
                           data['entry'][0].get('id')),
                     ('instagram_account_number', '=', data['entry'][0].get('id'))],
                    limit=1)
                account = accounts.filtered(lambda rec: rec.state == 'connected')
                if (account and data['entry'][0].get('messaging')[0].get(
                        'sender').get('id')
                        != account.instagram_account_number and
                        data['entry'][0].get('messaging')[0].get('sender').get(
                            'id') != account.instagram_business_account_number):
                    access_token = account.instagram_page_access_token
                    url = f"{account.instagram_base_url}/{recipient_id}?fields=id,name&access_token={access_token}"
                    response = requests.get(url, timeout=30)
                    discuss_channel_vals_list = []
                    members_to_add = request.env['res.partner'].sudo().search([])
                    discuss_channel_vals_list.append({
                        'instagram_account_number': data['entry'][0].get('id'),
                        'name': response.json().get('name'),
                        'description': "INSTAGRAM",
                    })
                    user_id = data['entry'][0].get('messaging')[0].get(
                        'sender').get('id')
                    url = f'https://graph.facebook.com/v18.0/{user_id}/'
                    params = {
                        'access_token': access_token,
                        'fields': 'id,name',
                    }
                    response = requests.get(url, params=params, timeout=30)
                    insta_user = response.json()
                    discuss_channels = request.env['discuss.channel'].sudo().search(
                        [('insta_partner_number', '=', insta_user.get('id'))])
                    if not discuss_channels:
                        discuss_channels = request.env['discuss.channel'].sudo().search(
                            [('instagram_account_number', '=',
                              data['entry'][0].get('id'))])
                    partner = request.env['res.partner'].sudo().search(
                        [('unique_ig_number', '=', insta_user['id'])])
                    lead = request.env['crm.lead'].sudo().search(
                        [('insta_user_number', '=', insta_user['id']),
                         ('type', '=', 'lead')])
                    sub_type_id = request.env.ref('mail.mt_comment').id
                    if not discuss_channels and not lead:
                        discuss_channels = request.env[
                            'discuss.channel'].sudo().create(
                            discuss_channel_vals_list)
                        discuss_channels.add_members(members_to_add.ids)
                    model = 'discuss.channel'
                    res_id = discuss_channels.id
                    if lead:
                        model = 'crm.lead'
                        res_id = lead.id
                        sub_type_id = request.env.ref(
                            'cyllo_instagram.mail_message_subtype_instagram_message').id
                    if not partner:
                        partner = request.env['res.partner'].sudo().create({
                            'name': insta_user['name'],
                            'unique_ig_number': insta_user['id'],
                            'insta_account_id': accounts.id
                        })
                    discuss_channels.add_members(partner.ids)
                    attachments = []
                    if data['entry'][0].get('messaging')[0].get('message').get(
                            'attachments'):
                        idx = data['entry'][0].get('messaging')[0].get(
                            'message').get('attachments')
                        attachments = request.env['ir.attachment'].sudo().create([
                            {'name': '',
                             'datas': base64.b64encode(requests.get(
                                 rec.get('payload').get('url'), timeout=30).content),
                             } for rec in idx
                        ])
                    message = request.env['mail.message'].sudo().create([{
                        'author_id': partner.id,
                        'subtype_id': sub_type_id,
                        'is_from_insta': True,
                        'is_possible_lead': True,
                        'email_from': data['entry'][0].get('messaging')[0].get(
                            'sender').get('id'),
                        'model': model,
                        'res_id': res_id,
                        'date': Datetime.now(),
                        'reply_to': False,
                        'insta_sender_number': recipient_id,
                        'body': data['entry'][0].get('messaging')[0].get(
                            'message').get('text') if data['entry'][0].get('messaging')[0].get(
                            'message').get('text') else 'image',
                        'attachment_ids': [(6, 0, [att.id for att in attachments])],
                    }])

                    if not lead:
                        data = {
                            "id": res_id,
                            "message": message.message_format()[0]
                        }
                        request.env["bus.bus"]._sendone(discuss_channels,
                                                        "discuss.channel/new_message",
                                                        data)
                    else:
                        channel = "REFRESH"
                        message = {
                            "message": message._message_notification_format(),
                        }
                        request.env["bus.bus"].sudo()._sendone(channel,
                                                               "notification",
                                                               message)
        except Exception:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _('Check the validity of your tokens'),
                    'type': 'warning',
                },
            }
