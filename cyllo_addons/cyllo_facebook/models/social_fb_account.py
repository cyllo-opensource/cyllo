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
from dateutil.relativedelta import relativedelta

from odoo import _, fields, models, api

_logger = logging.getLogger(__name__)


class SocialFbAccount(models.Model):
    """
    Class to define the fields and functions for Facebook Account.
    """
    _name = "social.fb.account"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Social Media Facebook Account"
    _rec_name = "facebook_page_name"

    facebook_access_token = fields.Char(string='Page Access Token', required=True,
                                        groups='cyllo_social_media_marketing.group_social_media_administrator',
                                        help="""Facebook Access Token provided by the Facebook API.""")
    facebook_user_access_token = fields.Char(string='User Access Token', required=True,
                                             groups='cyllo_social_media_marketing.group_social_media_administrator',
                                             help="""Facebook User Access Token provided by the Facebook API.""")
    facebook_page_number = fields.Char(string='Page ID', help="""Facebook Page ID provided by the Facebook API""")
    facebook_page_name = fields.Char(string='Page Name', required=True,
                                     help="""Facebook Page Name provided by the Facebook API""")
    facebook_base_url = fields.Char(string='Facebook Base Url Latest', required=True,
                                    default="https://graph.facebook.com/v18.0",
                                    help="""Base url of facebook integration update the latest version.""")
    facebook_connection_authenticated = fields.Boolean(string="Facebook Connection Completed", readonly=True,
                                                       help="Boolean signifies the connection of account")
    meta_app_number = fields.Char(string='Meta App Id', required=True, help="Meta account app id")
    meta_app_secret = fields.Char(string='Meta App Secrets', required=True,
                                  groups='cyllo_social_media_marketing.group_social_media_administrator',
                                  help="Meta account app secrets")
    expiry_date = fields.Date(string='Expiry Date of Access tokens',
                              help='Date at which access token must be refreshed')
    state = fields.Selection([('not connected', 'Not Connected'), ('connected', 'Connected')],
                             required=True, default='not connected', tracking=True)
    company_id = fields.Many2one(string="Related Company",
                                 comodel_name='res.company',
                                 default=lambda self: self.env.company.id,
                                 required=True, index=True,
                                 help="The company associated with the social media account.")
    is_default = fields.Boolean(string="Is Default", compute="_compute_is_default", store=False)
    followers_count = fields.Integer(string='Total Audience', readonly=True,
                                     help="Number of people who like/follow this Facebook Page (fan_count).")
    profile_picture_url = fields.Char(string='Profile Picture URL', readonly=True,
                                      help="Profile picture (dp) of the connected Facebook Page.")

    def _compute_is_default(self):
        default_id = self.env['ir.config_parameter'].sudo().get_param(
            'social_fb_account.default_fb_account_id'
        )
        for rec in self:
            rec.is_default = str(rec.id) == str(default_id)

    def action_connect(self):
        """ Function to connect Facebook account and authenticate the connection. """
        self = self.sudo()
        try:
            url = f'{self.facebook_base_url}/me/accounts?access_token={self.facebook_user_access_token}'
            response = requests.get(url, timeout=30).json()
            if response.get('error'):
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {'message': _(response.get('error')['message']), 'type': 'warning'},
                }
            if response.get('data') and self.facebook_page_name:
                name_list = []
                for data in response['data']:
                    name_list.append(data['name'])
                    if data['name'] == self.facebook_page_name:
                        self.write({
                            'facebook_page_number': data['id'],
                            'facebook_connection_authenticated': True,
                            'state': 'connected',

                        })
                        self.env['ir.config_parameter'].sudo().set_param(
                            'social_fb_account.default_fb_account_id', self.id
                        )
                        self._message_log(body="Page ID fetched Successfully.", )
                if self.facebook_page_name not in name_list:
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {'message': _("Page not found with given name"), 'type': 'warning'},
                    }
                self.refresh_access_token()
                if not self.expiry_date or self.expiry_date < fields.date.today():
                    self.refresh_access_token()
                self.action_fetch_audience()
            else:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {'message': _("Page not found.Fill the proper data and try again"), 'type': 'warning'},
                }
        except Exception:
            _logger.exception("Facebook action_connect failed for account id=%s", self.id)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _("Please verify that the provided credentials are accurate and ensure that "
                                 "your device is connected to the internet"),
                    'type': 'warning',
                },
            }

    def action_disconnect(self):
        """ Function to disconnect the Facebook account. """
        self.write({
            'state': 'not connected',
            'facebook_connection_authenticated': False,
        })
        self.env['ir.config_parameter'].sudo().set_param(
            'social_fb_account.default_fb_account_id', None
        )

    def action_default_fb(self):
        """Set this Facebook account as default."""
        self.env['ir.config_parameter'].sudo().set_param(
            'social_fb_account.default_fb_account_id', self.id
        )

    def action_fetch_audience(self):
        """ Fetch total audience (fan_count) for the connected Facebook Page. """
        for account in self.sudo():
            if not account.facebook_page_number or not account.facebook_access_token:
                continue
            url = f"{account.facebook_base_url}/{account.facebook_page_number}"
            params = {'fields': 'fan_count,picture.type(large)', 'access_token': account.facebook_access_token}
            response = requests.get(url, params=params, timeout=30).json()
            if response.get('fan_count') is not None:
                account.followers_count = response['fan_count']
            picture_url = response.get('picture', {}).get('data', {}).get('url')
            if picture_url:
                account.profile_picture_url = picture_url

    def refresh_access_token(self):
        """ Function to refresh the Facebook access token. """
        self = self.sudo()
        base_url = f"{self.facebook_base_url}/oauth/access_token"
        params = {
            'grant_type': 'fb_exchange_token',
            'client_id': self.meta_app_number,
            'client_secret': self.meta_app_secret,
            'fb_exchange_token': self.facebook_user_access_token,
        }
        response = requests.get(base_url, params=params, timeout=30)
        response.raise_for_status()
        result = response.json()
        long_lived_token = result.get('access_token')
        self.facebook_user_access_token = long_lived_token
        user_id_url = f"{self.facebook_base_url}/me?access_token={long_lived_token}"
        response = requests.get(user_id_url, timeout=30)
        user_id = response.json().get('id')
        long_live_page_token_url = f"{self.facebook_base_url}/{user_id}/accounts?access_token={long_lived_token}"
        response = requests.get(long_live_page_token_url, timeout=30)
        for page in response.json()['data']:
            if page.get('id') == self.facebook_page_number:
                self.facebook_access_token = page.get('access_token')
        self.expiry_date = fields.Date.today() + relativedelta(days=50)
