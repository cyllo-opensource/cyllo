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
import logging

import requests
from odoo import _, fields, models
from odoo.fields import Datetime

_logger = logging.getLogger(__name__)


class MailMessage(models.Model):
    """This class extends the 'mail.message' model in Odoo to include a new
    field indicating whether the message is from Facebook."""
    _inherit = 'mail.message'

    is_from_fb = fields.Boolean(string="From Facebook", help="Signifies Whether the message from Facebook.")
    fb_sender_number = fields.Char(string='Facebook Sender Id', help="""Id of Facebook sender""")

    def action_reply_message(self, reply):
        """Reply to a message. If the message is from Facebook, it sends the
        reply back via the Facebook API."""
        try:
            if self.is_from_fb:
                account = self.env['social.fb.account'].sudo().search([
                    ('facebook_page_number', '=', self.fb_sender_number), ('state', '=', 'connected')], limit=1)
                if account:
                    api_url = f"{account.facebook_base_url}/me/messages?access_token={account.facebook_access_token}"
                    headers = {"Content-Type": "application/json"}
                    data = {
                        "recipient": {"id": self.email_from},
                        "message": {"text": reply}
                    }
                    requests.post(api_url, json=data, headers=headers, timeout=30)
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'message': _("Reply has been sent"),
                            'type': 'success',
                        },
                    }
            return super().action_reply_message(reply)
        except Exception as e:
            _logger.exception("Facebook action_reply_message failed for message id=%s", self.id)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _(str(e)),
                    'type': 'warning',
                },
            }

    def action_create_lead(self):
        """ Action to view Facebook comments associated with the feed."""
        lead = self.env['crm.lead'].search([('mail_message_id', '=', self.id)])
        if lead:
            return lead.id
        if self.is_from_fb and not lead:
            lead = self.env['crm.lead'].create({
                'name': self.preview,
                'type': 'lead',
                'user_id': self.env.user.id,
                'partner_id': self.author_id.id,
                'contact_name': self.author_id.name,
                'mail_message_id': self.id,
                'fb_user_number': self.email_from,
            })
            return lead.id
        return super().action_create_lead()

    def action_reply_message_chatter(self, sender_id, reply, res_id):
        """Reply to a message from Facebook and create a corresponding mail
         message as a comment."""
        try:
            if self.is_from_fb:
                account = self.env['social.fb.account'].sudo().search(
                    [('facebook_page_number', '=', self.fb_sender_number), ('state', '=', 'connected')], limit=1)
                if account:
                    api_url = f"{account.facebook_base_url}/me/messages?access_token={account.facebook_access_token}"
                    headers = {"Content-Type": "application/json"}
                    data = {
                        "recipient": {"id": sender_id},
                        "message": {"text": reply}
                    }
                    requests.post(api_url, json=data, headers=headers, timeout=30)
                    if self.env['mail.message'].sudo().browse(res_id):
                        self.env['mail.message'].sudo().create([{
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
            return super().action_reply_message_chatter(sender_id, reply, res_id)
        except Exception as e:
            _logger.exception("Facebook action_reply_message_chatter failed for message id=%s", self.id)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _('This is an internal message, Nothing to make is an lead'),
                    'type': 'warning',
                },
            }
