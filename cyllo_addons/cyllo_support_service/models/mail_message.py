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

from odoo import models, _
from odoo.fields import Datetime


class MailMessage(models.Model):
    """This class extends the 'mail.message' model in Odoo to include a new
    field indicating whether the message is from Facebook."""
    _inherit = 'mail.message'

    def action_create_ticket(self):
        """Create or reuse a support ticket for this Facebook message.
        Returns the ticket ID if an open ticket already exists for the FB user,
        otherwise creates a new ticket and links it to this message."""

        ticket = self.env['support.service.ticket'].search(
            [('fb_user_number', '=', self.email_from), ('stage_id', 'not in', [
                self.env.ref(
                    'cyllo_support_service.support_service_stage_closed').id,
                self.env.ref(
                    'cyllo_support_service.support_service_stage_canceled').id,
                self.env.ref(
                    'cyllo_support_service.support_service_stage_solved').id])],
            limit=1)
        if ticket:
            return ticket.id
        if self.is_from_fb and not ticket:
            ticket = self.env['support.service.ticket'].create({
                'name': self.preview,
                'ticket_type': 'enquiries',
                'customer_id': self.author_id.id,
                'mail_message_id': self.id,
                'ticket_source': 'facebook',
                'fb_user_number': self.email_from,
            })
            return ticket.id

    def action_reply_message_chatter(self, sender_id, reply, res_id):
        """Reply to a message from Facebook and create a corresponding mail
         message as a comment."""
        try:
            if self.is_from_fb:
                account = self.env['social.fb.account'].sudo().search(
                    [('facebook_page_number', '=', self.fb_sender_number),
                     ('state', '=', 'connected')], limit=1)
                if account:
                    api_url = (f"{account.facebook_base_url}"
                               f"/me/messages?access_token="
                               f"{account.facebook_access_token}")
                    headers = {"Content-Type": "application/json"}
                    data = {
                        "recipient": {"id": sender_id},
                        "message": {"text": reply}
                    }
                    requests.post(api_url, json=data, headers=headers)
                    if self.env['support.service.ticket'].browse(res_id):
                        self.env['mail.message'].sudo().create([{
                            'author_id': self.env.user.partner_id.id,
                            'subtype_id': self.env.ref('mail.mt_comment').id,
                            'model': 'support.service.ticket',
                            'res_id': res_id,
                            'date': Datetime.now(),
                            'reply_to': False,
                            'body': reply,
                        }])
                    if self.env['support.service.ticket'].browse(res_id):
                        self.env['crm.lead'].sudo().create([{
                            'author_id': self.env.user.partner_id.id,
                            'subtype_id': self.env.ref('mail.mt_comment').id,
                            'model': 'crm.lead',
                            'res_id': res_id,
                            'date': Datetime.now(),
                            'reply_to': False,
                            'body': reply,
                        }])
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'message': _("Reply has been sent"),
                            'type': 'success',
                        },
                    }
        except Exception:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _('This is an internal message, Nothing '
                                 'to make is an lead'),
                    'type': 'warning',
                },
            }
