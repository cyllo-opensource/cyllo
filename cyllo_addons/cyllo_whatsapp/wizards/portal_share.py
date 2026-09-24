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
from odoo.exceptions import RedirectWarning


class PortalShare(models.TransientModel):
    """Extends the 'portal.share' model to add functionality for sharing through WhatsApp."""
    _inherit = 'portal.share'

    share_whatsapp = fields.Boolean(string="Share Through Whatsapp",
                                    help="Enable this to share link through whatsapp if the customer have"
                                         " whatsapp account")

    def action_send_mail(self):
        """Override the action_send_mail method to include WhatsApp sharing if enabled."""
        if self.share_whatsapp:
            self.action_whatsapp_message()
        return super().action_send_mail()

    def action_whatsapp_message(self):
        """
            Sends WhatsApp message to the selected partners with the shared link.
            Raises:
                RedirectWarning: If the user's WhatsApp account is not configured.
        """
        if not self.env.user.token or not self.env.user.phone_uid:
            action_error = {
                'name': _('User'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'res.users',
                'views': [[self.env.ref('base.view_users_form').id, 'form']],
                'target': 'current',
                'res_id': self.env.user.id,
            }
            msg = _('Configure the WhatsApp account to share.')
            raise RedirectWarning(msg, action_error, _('Go to the configuration menu'))
        else:
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.env.user.token}'
            }
            model = self.env['ir.model'].search([('model', '=', self.res_model)])
            for partner in self.partner_ids:
                if partner.whatsapp_number:
                    # Customize the message with dynamic values
                    message_content = (f"Dear {partner.name},\n\n{self.env.user.name} has invited you to access "
                                       f"the following {model.name}:\n\nLink: {self.share_link}")
                    payload = {"messaging_product": "whatsapp", "recipient_type": "individual", "type": "text",
                               "text": {"preview_url": False, "body": message_content}, "to": partner.whatsapp_number}
                    try:
                        requests.post(f"https://graph.facebook.com/v17.0/{self.env.user.phone_uid}/messages",
                                      json=payload, headers=headers)
                    except requests.exceptions.HTTPError as e:
                        raise e
