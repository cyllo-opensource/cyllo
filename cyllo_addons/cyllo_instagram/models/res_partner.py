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
    """
    Inherits the base res.partner model and adds Tasks information in the partner form.
    """
    _inherit = 'res.partner'

    post_id = fields.Many2one('social.media.post', string='Post Related to Partner',
                              help="The post where this contact was created.")
    unique_ig_number = fields.Char(string='Instagram Id', help="Unique identifier for the partner's feed on Facebook.")
    insta_account_id = fields.Many2one('social.insta.account', string='Instagram Account',
                                       help="Account related to partner")
    is_insta_chat = fields.Boolean(string="Instagram Chat", help="Available in Instagram chat")
    insta_chat = fields.Char(string='Chat Content', help="Last chat content.")
    insta_chat_time = fields.Datetime(string="Chat Time", help="Time of chat")

    def action_message_partner_insta(self, reply):
        """Function  to message partner through instagram"""
        account = self.insta_account_id.sudo()
        self.write({
            'is_insta_chat': True,
            'insta_chat': reply,
            'insta_chat_time': fields.datetime.today()
        })
        if account and self.unique_ig_number:
            api_url = f"{account.instagram_base_url}/me/messages?access_token={account.instagram_page_access_token}"
            requests.post(api_url, json={
                "recipient": {"id": self.unique_ig_number},
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
