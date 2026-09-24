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


class ResPartner(models.Model):
    """Inherits the base res.partner model and adds Tasks information in
    the partner form."""
    _inherit = 'res.partner'

    post_id = fields.Many2one('social.media.post', string='Post from Contact Created',
                              help="The post where this contact was created.")
    unique_fb_number = fields.Char(string='Unique Facebook Id',
                                   help="Unique identifier for the partner's feed on Facebook.")
    fb_account_id = fields.Many2one('social.fb.account', string='Facebook Account', help="Account")
    is_fb_chat = fields.Boolean(string="Facebook Chat", help="Available in Facebook chat")
    fb_chat = fields.Char(string='Chat Content', help="Last chat content.")
    fb_chat_time = fields.Datetime(string="Chat Time", help="Time of chat")

    def action_message_partner_fb(self, reply):
        """Function to message partner from the chatter directly"""
        account = self.fb_account_id.sudo()
        self.write({
            'is_fb_chat': True,
            'fb_chat': reply,
            'fb_chat_time': fields.datetime.today()
        })
        if account and self.unique_fb_number:
            api_url = f"{account.facebook_base_url}/me/messages?access_token={account.facebook_access_token}"
            headers = {"Content-Type": "application/json"}
            data = {
                "recipient": {"id": self.unique_fb_number},
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
