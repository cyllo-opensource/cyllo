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
import requests

from odoo import http
from odoo.fields import Datetime
from odoo.http import request

from odoo.addons.cyllo_facebook.controllers import main



class TicketWebHook(main.WebHook):
    """Controller handling Facebook webhook interactions."""

    @http.route('/facebook/webhook/', methods=['POST'], type="json",
                auth="public")
    def get_message_data(self):
        """Extracts message data from the incoming webhook request."""
        res = super(TicketWebHook, self).get_message_data()
        data = request.get_json_data()

        account = request.env['social.fb.account'].sudo().search(
            [('facebook_page_number', '=', data['entry'][0].get('id')),
             ('state', '=', 'connected')], limit=1)
        if account:
            access_token = account.facebook_access_token
            user_id = data['entry'][0].get('messaging')[0].get('sender')[
                'id']
            recipient_id = data['entry'][0].get('id')
            url = (f"{account.facebook_base_url}"
                   f"/{user_id}"
                   f"?fields=id,name,picture&access_token={access_token}")
            fb_user = requests.get(url).json()
            ticket = request.env['support.service.ticket'].sudo().search(
                [('fb_user_number', '=', fb_user['id']),
                 ('stage_id', 'not in', [
                     request.env.ref(
                         'cyllo_support_service.support_service_stage_closed').id,
                     request.env.ref(
                         'cyllo_support_service.support_service_stage_canceled').id,
                     request.env.ref(
                         'cyllo_support_service.support_service_stage_solved').id])],
            )
            partner = request.env['res.partner'].sudo().search(
                [('unique_fb_number', '=', fb_user['id'])])
            if ticket:
                if data['entry'][0].get('messaging')[0].get('message') != None:
                    message = request.env['mail.message'].sudo().create([{
                        'author_id': partner.id,
                        'subtype_id': request.env.ref(
                            'cyllo_facebook.mail_message_subtype_facebook_message').id,
                        'is_from_fb': True,
                        'email_from':
                            data['entry'][0].get('messaging')[0].get('sender')[
                                'id'],
                        'model': 'support.service.ticket',
                        'res_id': ticket.id,
                        'date': Datetime.now(),
                        'reply_to': False,
                        'fb_sender_number': recipient_id,
                        'body':
                            data['entry'][0].get('messaging')[0].get('message')[
                                'text']
                    }])
                    message = {
                        "message": message._message_notification_format(),
                    }
                    request.env["bus.bus"].sudo()._sendone("REFRESH",
                                                           "notification",
                                                           message)
        return res
