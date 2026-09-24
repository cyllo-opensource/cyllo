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
from werkzeug.exceptions import Forbidden
from http import HTTPStatus
from odoo import _, fields, http
from odoo.fields import Datetime
from odoo.http import request

_logger = logging.getLogger(__name__)


class WebHook(http.Controller):
    """Controller handling Facebook webhook interactions."""

    @http.route('/facebook/webhook/', methods=['GET'], type="http", auth="public", csrf=False)
    def receive_message(self, **kwargs):
        """Handle GET requests to the Facebook webhook."""
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
        """ Meta signs every webhook POST body with the app secret
        (X-Hub-Signature-256: sha256=<hex hmac>) - without checking it,
        anyone can POST forged payloads to this public, unauthenticated
        endpoint (fake messages/leads, or an attacker-chosen URL for us to
        fetch via requests.get() as an SSRF vector). We don't know which
        connected account's app secret applies until the payload itself is
        parsed, so try every distinct secret in use and accept if any
        matches. """
        signature_header = request.httprequest.headers.get('X-Hub-Signature-256', '')
        if not signature_header.startswith('sha256='):
            return False
        provided = signature_header.split('=', 1)[1]
        raw_body = request.httprequest.get_data()
        secrets = request.env['social.fb.account'].sudo().search(
            [('meta_app_secret', '!=', False)]).mapped('meta_app_secret')
        for secret in set(secrets):
            expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
            if hmac.compare_digest(expected, provided):
                return True
        return False

    @http.route('/facebook/webhook/', methods=['POST'], type="json", auth="public")
    def get_message_data(self):
        """Handle POST requests containing Facebook message data."""
        if not self._verify_signature():
            _logger.warning("Facebook webhook: rejected POST with invalid/missing signature.")
            raise Forbidden()
        try:
            data = request.get_json_data()
            if not data['entry'][0].get('messaging')[0].get(
                    'message').get('is_echo'):
                account = request.env['social.fb.account'].sudo().search(
                    [('facebook_page_number', '=', data['entry'][0].get('id')), ('state', '=', 'connected')], limit=1)
                if account:
                    if account.expiry_date < fields.date.today():
                        account.refresh_access_token()
                    recipient_id = data['entry'][0].get('id')
                    url = (f'{account.facebook_base_url}/{recipient_id}?fields=id,name,category&access_token='
                           f'{account.facebook_access_token}')
                    response = requests.get(url, timeout=30)
                    discuss_channel_vals_list = []
                    members_to_add = request.env['res.partner'].sudo().search([])
                    discuss_channel_vals_list.append({
                        'fb_page_number': data['entry'][0].get('id'),
                        'name': response.json().get('name'),
                        'description': "FACEBOOK",
                    })


                    access_token = account.facebook_access_token
                    user_id = data['entry'][0].get('messaging')[0].get('sender')['id']
                    url = f"{account.facebook_base_url}/{user_id}?fields=id,name,picture&access_token={access_token}"
                    fb_user = requests.get(url, timeout=30).json()
                    discuss_channels = request.env['discuss.channel'].sudo().search(
                        [('fb_partner_number', '=', fb_user.get('id'))])
                    if not discuss_channels:
                        discuss_channels = request.env[
                            'discuss.channel'].sudo().search(
                            [('fb_page_number', '=', data['entry'][0].get('id'))])
                    image_url = fb_user['picture']['data']['url']
                    image = base64.b64encode(requests.get(image_url, timeout=30).content).decode('utf-8')
                    partner = request.env['res.partner'].sudo().search([('unique_fb_number', '=', fb_user['id'])])
                    lead = request.env['crm.lead'].sudo().search([('fb_user_number', '=', fb_user['id']),
                                                                  ('type', '=', 'lead')])
                    sub_type_id = request.env.ref('mail.mt_comment').id
                    if not discuss_channels and not lead:
                        discuss_channels = request.env['discuss.channel'].sudo().create(discuss_channel_vals_list)
                        discuss_channels.add_members(members_to_add.ids)
                    model = 'discuss.channel'
                    res_id = discuss_channels.id
                    if lead:
                        model = 'crm.lead'
                        res_id = lead.id
                        sub_type_id = request.env.ref('cyllo_facebook.mail_message_subtype_facebook_message').id
                    if not partner:
                        partner = request.env['res.partner'].sudo().create({
                            'name': fb_user['name'],
                            'unique_fb_number': fb_user['id'],
                            'image_1920': image,
                            'fb_account_id': account.id
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
                        'is_from_fb': True,
                        'is_possible_lead': True,
                        'email_from': data['entry'][0].get('messaging')[0].get('sender')['id'],
                        'model': model,
                        'res_id': res_id,
                        'date': Datetime.now(),
                        'reply_to': False,
                        'fb_sender_number': recipient_id,
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
                        request.env["bus.bus"]._sendone(discuss_channels, "discuss.channel/new_message", data)
                    else:
                        channel = "REFRESH"
                        message = {"message": message._message_notification_format()}
                        request.env["bus.bus"].sudo()._sendone(channel, "notification", message)
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _(e),
                    'type': 'warning',
                },
            }
