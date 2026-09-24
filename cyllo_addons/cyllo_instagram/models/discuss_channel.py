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



class DiscussChannel(models.Model):
    """This class extends the 'discuss.channel' model in Odoo to include a new field for storing the
    Instagram Page ID."""
    _inherit = 'discuss.channel'

    instagram_account_number = fields.Char(string="Instagram Account Id",
                                           help="Id of Instagram Account")
    insta_partner_number = fields.Char(string="Instagram Partner Id",
                                           help="Id of Instagram Partner")

    def action_find_partner_insta(self):
        return {
            'partner': self.channel_partner_ids.filtered(
                lambda l: l.id != self.env.user.partner_id.id),
            'instagram': self.insta_partner_number if self.insta_partner_number else False,
        }

    def action_message_chat_discuss_insta(self, message):
        account = self.channel_partner_ids.sudo().filtered(
            lambda l: l.id != self.env.user.partner_id.id).insta_account_id
        if account and self.insta_partner_number:
            api_url = f"{account.instagram_base_url}/me/messages?access_token={account.instagram_page_access_token}"
            requests.post(api_url, json={
                "recipient": {"id": self.insta_partner_number},
                "message": {"text": message}
            }, headers={"Content-Type": "application/json"}, timeout=30)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _("Reply has been sent"),
                    'type': 'success',
                },
            }
