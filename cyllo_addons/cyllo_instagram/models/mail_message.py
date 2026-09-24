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
from odoo import _, fields, models
from odoo.fields import Datetime


class MailMessage(models.Model):
    """This class extends the 'mail.message' model in Odoo to include a new field indicating whether the message is
    from Instagram."""
    _inherit = 'mail.message'

    is_from_insta = fields.Boolean(string="From Instagram", help="Signifies Whether the message from Instagram.")
    insta_sender_number = fields.Char(string='Instagram Sender Id', help="""Id of instagram sender""")

    def action_reply_message(self, reply):
        """Reply to a message. If the message is from Instagram, it sends the reply back via the Instagram API."""
        try:
            if self.is_from_insta:
                accounts = self.env['social.insta.account'].sudo().search(
                    ['|', ('instagram_business_account_number', '=', self.insta_sender_number),
                     ('instagram_account_number', '=', self.insta_sender_number)], limit=1)
                account = accounts.filtered(lambda rec: rec.state == 'connected')
                if account:
                    api_url = (f"{account.instagram_base_url}/me/messages?access_token="
                               f"{account.instagram_page_access_token}")
                    requests.post(api_url, json={
                        "recipient": {"id": self.email_from},
                        "message": {"text": reply}
                    }, headers={"Content-Type": "application/json"}, timeout=30)
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
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _(e),
                    'type': 'warning',
                },
            }

    def action_create_lead(self):
        """ Action to create lead on the basis of message."""
        lead = self.env['crm.lead'].search([('mail_message_id', '=', self.id)])
        if lead:
            return lead.id
        if self.is_from_insta and not lead:
            lead = self.env['crm.lead'].create({
                'name': self.preview,
                'type': 'lead',
                'user_id': self.env.user.id,
                'partner_id': self.author_id.id,
                'contact_name': self.author_id.name,
                'mail_message_id': self.id,
                'insta_user_number': self.email_from,
            })
            return lead.id
        return super().action_create_lead()

    def action_reply_message_chatter(self, sender_id, reply, res_id):
        """Reply to a message from Instagram and create a corresponding mail message as a comment."""
        try:
            if self.is_from_insta:
                accounts = self.env['social.insta.account'].sudo().search(
                    ['|', ('instagram_business_account_number', '=', self.insta_sender_number),
                     ('instagram_account_number', '=', self.insta_sender_number)], limit=1)
                account = accounts.filtered(lambda rec: rec.state == 'connected')
                if account:
                    api_url = (f"{account.instagram_base_url}/me/messages?access_token="
                               f"{account.instagram_page_access_token}")
                    requests.post(api_url, json={
                        "recipient": {"id": sender_id},
                        "message": {"text": reply}
                    }, headers={"Content-Type": "application/json"}, timeout=30)
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
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _(e),
                    'type': 'warning',
                },
            }
