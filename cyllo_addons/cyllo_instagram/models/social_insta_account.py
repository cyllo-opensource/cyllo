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
import secrets

import requests
from dateutil.relativedelta import relativedelta

from odoo import _, fields, models
from odoo.exceptions import ValidationError
from werkzeug.urls import url_encode, url_join

_logger = logging.getLogger(__name__)


class SocialInstaAccount(models.Model):
    """Class to define the fields and functions for Facebook Account."""
    _name = "social.insta.account"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Social Media Instagram Account"
    _rec_name = "facebook_insta_page_name"

    instagram_access_token = fields.Char(string='Access Token', required=True,
                                         groups='cyllo_social_media_marketing.group_social_media_administrator',
                                         help="""Instagram Access Token provided by the Facebook API.""")
    instagram_page_access_token = fields.Char(string='Facebook Page Access Token', required=True,
                                              groups='cyllo_social_media_marketing.group_social_media_administrator',
                                              help="""Facebook Page Access Token provided by the Facebook API.""")
    facebook_insta_page_number = fields.Char(string='Page ID', help="""Facebook Page ID provided by the Facebook API""")
    facebook_insta_page_name = fields.Char(string='Page Name', required=True,
                                           help="""Facebook Page Name provided by the Facebook API""")
    instagram_base_url = fields.Char(string='Instagram Base Url Latest', required=True,
                                     default="https://graph.facebook.com/v18.0",
                                     help="""Base url of Instagram integration update the latest version.""")
    instagram_connection_authenticated = fields.Boolean(string="Instagram Connection Completed",
                                                        help="Boolean field which signifies the connection.")
    meta_app_number = fields.Char(string='Meta App Id', required=True, help="Meta account app id")
    meta_app_secret = fields.Char(string='Meta App Secrets', required=True,
                                  groups='cyllo_social_media_marketing.group_social_media_administrator',
                                  help="Meta account app secrets")
    renewal_date = fields.Date(string='Renewal Date of Access Token', help="Date for the renewal, the access token must"
                                                                           " be renewed within 5 days after this day")
    instagram_account_number = fields.Char(string='Instagram Id', help="Connected Instagram account id.")
    instagram_business_account_number = fields.Char(string='Instagram Business Id',
                                                    help="Connected Instagram account id.")
    company_id = fields.Many2one(string="Related Company",
                                 comodel_name='res.company',
                                 default=lambda self: self.env.company.id,
                                 required=True, index=True,
                                 help="The company associated with the social media account.")
    state = fields.Selection([('not connected', 'Not Connected'), ('connected', 'Connected')],
                             required=True, default='not connected', tracking=True)
    is_default = fields.Boolean(string="Is Default", compute="_compute_is_default", store=False)
    followers_count = fields.Integer(string='Total Audience', readonly=True,
                                     help="Number of followers of this Instagram business account.")
    profile_picture_url = fields.Char(string='Profile Picture URL', readonly=True,
                                      help="Profile picture (dp) of the connected Instagram business account.")
    oauth_nonce = fields.Char(readonly=True, copy=False,
                              help="One-time random token proving the OAuth callback for this account "
                                   "was actually triggered by us, not guessed/forged (the old "
                                   "'insta_<account_id>' state was just the account id with a prefix - "
                                   "trivially guessable, letting anyone bind their own Facebook identity "
                                   "to any account id). Cleared once the callback consumes it.")

    def _compute_is_default(self):
        default_id = self.env['ir.config_parameter'].sudo().get_param(
            'social_insta_account.default_insta_account_id'
        )
        for rec in self:
            rec.is_default = str(rec.id) == str(default_id)

    def action_connect_instagram(self):
        """Function to connect Instagram account and authenticate the connection."""
        self = self.sudo()
        try:
            url = f'{self.instagram_base_url}/me/accounts?access_token={self.instagram_access_token}'
            response = requests.get(url, timeout=30).json()
            if response.get('error'):
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {'message': _(response.get('error')['message']), 'type': 'warning'},
                }
            if response.get('data') and self.facebook_insta_page_name:
                name_list = []
                for data in response['data']:
                    name_list.append(data['name'])
                    if data['name'] == self.facebook_insta_page_name:
                        self.write({'facebook_insta_page_number': data['id']})
                        self._message_log(body="Page ID fetched Successfully")
                if self.facebook_insta_page_name not in name_list:
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {'message': _("Page not found with given name"), 'type': 'warning'},
                    }
                business_url = (f"{self.instagram_base_url}/{self.facebook_insta_page_number}?fields=id,name,"
                                f"instagram_business_account&access_token={self.instagram_page_access_token}")
                business_url_response = requests.get(business_url, timeout=30).json()
                if not business_url_response.get('instagram_business_account'):
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'message': _("This Facebook page has no linked Instagram business account."),
                            'type': 'warning',
                        },
                    }
                self.instagram_business_account_number = business_url_response['instagram_business_account']['id']
                insta_url = (f"{self.instagram_base_url}/{self.facebook_insta_page_number}/instagram_accounts?"
                             f"access_token={self.instagram_page_access_token}&fields=id,username")
                datas = requests.get(insta_url, timeout=30).json()
                if not datas.get('data'):
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'message': _(datas.get('error', {}).get('message')
                                        or "Could not fetch the Instagram account for this page."),
                            'type': 'warning',
                        },
                    }
                self.instagram_account_number = datas['data'][0].get('id')
                if not self.renewal_date or self.renewal_date < fields.date.today():
                    self.refresh_access_token()
                self.write({
                            'state': 'connected',
                            'instagram_connection_authenticated': True
                })
                self.action_fetch_audience()

                self.env['ir.config_parameter'].sudo().set_param(
                    'social_insta_account.default_insta_account_id', self.id
                )
            else:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': _("Page not found.Fill the proper data and try again"),
                        'type': 'warning',
                    },
                }
        except Exception:
            _logger.exception("Instagram manual connect failed for account %s", self.id)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _("Please verify that the provided credentials are accurate and ensure that your device "
                                 "is connected to the internet"),
                    'type': 'warning',
                },
            }

    def action_connect_instagram_oauth(self):
        """Connect Instagram account via Facebook OAuth."""
        self.ensure_one()
        if not self.meta_app_number or not self.meta_app_secret:
            raise ValidationError(_(
                'Meta App Id and Meta App Secrets are required!\n'
                'Please fill them in before connecting with Facebook.'
            ))
        if not self.facebook_insta_page_name:
            raise ValidationError(_(
                'Page Name is required!\n'
                'Enter the exact Facebook Page name to connect before using OAuth.'
            ))
        nonce = secrets.token_urlsafe(32)
        self.oauth_nonce = nonce
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        redirect_uri = url_join(base_url, '/instagram/oauth/callback')
        params = {
            'response_type': 'code',
            'client_id': self.meta_app_number,
            'redirect_uri': redirect_uri,
            'state': nonce,
            'scope': (
                'pages_show_list,pages_read_engagement,pages_manage_metadata,'
                'instagram_basic,instagram_manage_messages,instagram_manage_comments,'
                'business_management'
            ),
        }
        return {
            'type': 'ir.actions.act_url',
            'url': 'https://www.facebook.com/v18.0/dialog/oauth?%s' % url_encode(params),
            'target': 'self',
        }

    def action_disconnect(self):
        """Function to disconnect the Instagram account."""
        self.write({
            'state': 'not connected',
            'instagram_connection_authenticated': False,
            'renewal_date': False,
        })
        self.env['ir.config_parameter'].sudo().set_param(
            'social_insta_account.default_insta_account_id', None
        )

    def action_default_ig(self):
        self.env['ir.config_parameter'].sudo().set_param(
            'social_insta_account.default_insta_account_id', self.id
        )

    def action_fetch_audience(self):
        """ Fetch total audience (followers_count) for the connected Instagram business account. """
        self = self.sudo()
        for account in self:
            if not account.instagram_business_account_number or not account.instagram_page_access_token:
                continue
            url = f"{account.instagram_base_url}/{account.instagram_business_account_number}"
            params = {'fields': 'followers_count,profile_picture_url', 'access_token': account.instagram_page_access_token}
            response = requests.get(url, params=params, timeout=30).json()
            if response.get('followers_count') is not None:
                account.followers_count = response['followers_count']
            if response.get('profile_picture_url'):
                account.profile_picture_url = response['profile_picture_url']

    def refresh_access_token(self):
        """Function to refresh the Instagram access token."""
        self = self.sudo()
        base_url = f"{self.instagram_base_url}/oauth/access_token"
        params = {
            'grant_type': 'fb_exchange_token',
            'client_id': self.meta_app_number,
            'client_secret': self.meta_app_secret,
            'fb_exchange_token': self.instagram_access_token,
        }
        response = requests.get(base_url, params=params, timeout=30)
        response.raise_for_status()
        result = response.json()
        long_lived_token = result.get('access_token')
        self.instagram_access_token = long_lived_token
        user_id_url = f"{self.instagram_base_url}/me?access_token={long_lived_token}"
        response = requests.get(user_id_url, timeout=30)
        user_id = response.json().get('id')
        long_live_page_token_url = f"{self.instagram_base_url}/{user_id}/accounts?access_token={long_lived_token}"
        response = requests.get(long_live_page_token_url, timeout=30)
        for page in response.json()['data']:
            if page.get('id') == self.facebook_insta_page_number:
                self.instagram_page_access_token = page.get('access_token')
        self.renewal_date = fields.Date.today() + relativedelta(days=50)
