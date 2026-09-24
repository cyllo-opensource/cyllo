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
from odoo import api, fields, models

GOOGLE_AUTH_ENDPOINT = 'https://accounts.google.com/o/oauth2/auth'
GOOGLE_TOKEN_ENDPOINT = 'https://accounts.google.com/o/oauth2/token'


class DropboxAuthCode(models.TransientModel):
    """Wizard to handle authentication for backup configuration.
    This wizards allows users to enter the Dropbox authorization code and
    sets up the Dropbox refresh token."""
    _name = 'dropbox.auth.code'
    _description = 'Authentication Code Wizard'

    dropbox_authorization_code = fields.Char(
        help='The authorization code of dropbox')
    dropbox_auth_url = fields.Char(string='Dropbox Authentication URL',
                                   compute='_compute_dropbox_auth_url',
                                   help='Dropbox authentication URL')

    @api.depends('dropbox_authorization_code')
    def _compute_dropbox_auth_url(self):
        """Compute method to generate the Dropbox authentication URL based on
        the provided authorization code."""
        backup_config = self.env['db.backup.configure'].browse(
            self.env.context.get('active_id'))
        for rec in self:
            rec.dropbox_auth_url = backup_config.get_dropbox_auth_url()

    def action_setup_dropbox_token(self):
        """Action method to set up the Dropbox refresh token using the
        provided authorization code."""
        backup_config = self.env['db.backup.configure'].browse(
            self.env.context.get('active_id'))
        try:
            backup_config.set_dropbox_refresh_token(
                self.dropbox_authorization_code)
        except Exception as e:
            error_message = "An error occurred while setting the Dropbox refresh token."
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': "Refresh token setting Failed",
                    'message': error_message,
                    'type': 'danger',
                    'sticky': True,
                }
            }
