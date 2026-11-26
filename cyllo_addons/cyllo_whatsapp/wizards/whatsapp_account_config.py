# -*- coding: utf-8 -*-
#############################################################################
#
#    Cyllo Pvt. Ltd.
#
#    Copyright (C) 2025-TODAY Cyllo(<https://www.cyllo.com>)
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
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class WhatsappAccountConfig(models.TransientModel):
    """Transient model used by the 'Whatsapp' client action to configure the
    Facebook / Whatsapp credentials (App ID, Phone Number ID, Business
    Account ID and Access Token) of the current user. The values are
    pre-filled with the existing configuration and are saved on
    'res.users' when the user clicks on the Continue button."""
    _name = 'whatsapp.account.config'
    _description = 'Whatsapp Account Configuration'

    user_id = fields.Many2one('res.users', string='User', required=True,
                              default=lambda self: self.env.user)
    app_uid = fields.Char(string='App ID', required=True,
                          help='The Facebook application ID')
    phone_uid = fields.Char(string='Phone Number ID', required=True,
                            help='Enter the whatsapp phone number ID')
    account_uid = fields.Char(string='Business Account ID', required=True,
                              help='The Whatsapp business account ID')
    token = fields.Char(string='Access Token', required=True,
                        help='Enter the whatsapp access token')

    @api.model
    def default_get(self, fields_list):
        """Pre-fill the wizard with the credentials of the current user."""
        res = super().default_get(fields_list)
        user = self.env.user.sudo()
        res.update({
            'app_uid': user.app_uid or False,
            'phone_uid': user.phone_uid or False,
            'account_uid': user.account_uid or False,
            'token': user.token or False,
        })
        return res

    def action_update_data(self):
        """Save the credentials on the wizard user and close the dialog."""
        self.ensure_one()
        if not self.user_id:
            raise ValidationError(
                _('Please select the user for which you want to configure '
                  'the Whatsapp account.'))
        self.user_id.sudo().write({
            'account_uid': self.account_uid,
            'app_uid': self.app_uid,
            'phone_uid': self.phone_uid,
            'token': self.token,
        })
        return {'type': 'ir.actions.act_window_close'}
