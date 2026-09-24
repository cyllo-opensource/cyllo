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
import secrets
import string

from odoo import _, api, fields, models


class ResUser(models.Model):
    """Extend the Odoo 'res.users' model to include additional fields related to
    WhatsApp integration for business accounts."""
    _inherit = 'res.users'

    phone_uid = fields.Char(string="Phone Number ID",
                            help="Enter the whatsapp phone number ID")
    token = fields.Char(string="Access Token",
                        help="Enter the whatsapp access token")
    webhook_callback_url = fields.Char(string="Callback URL",
                                       compute='_compute_webhook_callback_url',
                                       copy=False,
                                       help="The url foe Webhook configuration")
    return_token = fields.Char(string="Verification Token", readonly=True)
    app_uid = fields.Char(string="App ID", help="The Facebook application ID",
                          tracking=True)
    account_uid = fields.Char(string="Business Account ID", tracking=True,
                              help="The Whatsapp business account ID")
    user_ids = fields.Many2many('res.users', 'whatsapp_comfig_rel', 'cid',
                                domain=lambda self: [('share', '=', False)],
                                string='Share Account With')

    def action_config_whatsapp_account(self):
        """ Set webhook_verify_token only when record is created, not updated after that."""
        if self.phone_uid and self.account_uid and self.app_uid and self.token:
            for user in self._origin.user_ids:
                if user.id not in self._origin.ids:
                    user.sudo().write({
                        'phone_uid': self.phone_uid,
                        'account_uid': self.account_uid,
                        'app_uid': self.app_uid,
                        'token': self.token,
                    })
            self.user_ids = False
        else:
            self.user_ids = False
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _(
                        "Account details such as App ID, Business Account Id, Phone Number Id, "
                        "Access Token have to be filled to share this account."),
                    'type': 'warning',
                },
            }

    def _compute_webhook_callback_url(self):
        """Compute the callback URL for the current record.
        This method generates a callback URL by combining the base URL of the
        Odoo instance with the endpoint '/whatsapp/message'. The resulting URL
        is assigned to the 'webhook_callback_url' field
        of the current record.
        :return: None"""
        for record in self:
            record.webhook_callback_url = record.get_base_url() + '/whatsapp/message'

    def get_user_data(self, uid):
        """Retrieves user data based on user ID.
            Args:
                uid (int): The ID of the user.
            Returns:
                dict: A dictionary containing user data including token, phone UID, app UID, and account UID."""
        user = self.sudo().browse(uid)
        return {
            'id': user.id,
            'name': user.name,
            'user_email': user.email,
            'token': user.token,
            'phone_uid': user.phone_uid,
            'app_uid': user.app_uid,
            'account_uid': user.account_uid,
        }

    def action_update_data(self, account_uid, app_uid, phone_uid, token):
        """Updates user data with the provided values.
            Args:
                account_uid (int): The account UID to update.
                app_uid (int): The app UID to update.
                phone_uid (int): The phone UID to update.
                token (str): The token to update.
            Returns:
                None"""
        self.sudo().write({
            'account_uid': account_uid,
            'app_uid': app_uid,
            'phone_uid': phone_uid,
            'token': token,
        })

    def action_update_profile_data(self, user_email, user_name):
        """Updates user data with the provided values."""
        self.sudo().write({
            'email': user_email,
            'name': user_name,
        })

    def action_generate_token(self):
        self.ensure_one()
        if self.phone_uid and self.app_uid and self.token and self.account_uid:
            alphabet = string.ascii_letters + string.digits
            return_token = ''.join(secrets.choice(alphabet) for _ in range(7))
            self.return_token = return_token
            self.env['ir.config_parameter'].sudo().set_param(
                'res_users.whatsapp_return_token', return_token
            )

    @api.model
    def get_whatsapp_user_view(self):
        """Retrieves the view of the WhatsApp user.
        This method returns the view of the WhatsApp user by accessing the view with the reference
        'cyllo_whatsapp.view_res_users_form'.
        Returns:
           dict: A dictionary representing the view of the WhatsApp user."""
        return self.env.ref("cyllo_whatsapp.view_res_users_form").sudo().read()

    @api.model
    def get_whatsapp_user_view_config(self):
        """Retrieves the view of the WhatsApp user.
        This method returns the view of the WhatsApp user by accessing the view with the reference
        'cyllo_whatsapp.view_res_users_form'.
        Returns:
           dict: A dictionary representing the view of the WhatsApp user."""
        return self.env.ref(
            "cyllo_whatsapp.view_res_users_form_config").sudo().read()

    @api.model
    def get_whatsapp_configuration(self):
        datas = self.sudo().search_read([('id', '=', self.env.user.id)], [
            'app_uid', 'account_uid', 'token', 'phone_uid'
        ])
        if datas and all(datas[0][key] for key in
                         ['app_uid', 'account_uid', 'token', 'phone_uid']):
            return True
        else:
            return False

    import base64

    def change_profile_picture(self, profile_picture):
        # Check if the input is a base64 image string and clean the prefix
        if profile_picture.startswith('data:image'):
            profile_picture = profile_picture.split(',')[
                1]  # Remove the data:image/jpeg;base64, part

        # Write the cleaned base64 image string directly into the image_1920 field
        self.sudo().write({
            'image_1920': profile_picture
        })

        return True
