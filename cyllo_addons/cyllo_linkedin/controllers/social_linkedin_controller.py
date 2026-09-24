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

import requests
from odoo import http, _
from odoo.http import request
from werkzeug.urls import url_join


class LinkedInSocialController(http.Controller):

    @http.route('/linkedin/redirect', type='http', auth='user', website=True)
    def social_linkedin_callbacks(self, **kw):
        """
        Handle LinkedIn OAuth callback.
        """
        state = kw.get('state')
        linkedin_account = request.env['linkedin.account'].sudo().search(
            [('oauth_nonce', '=', state)], limit=1) if state else request.env['linkedin.account']
        is_new_pending = False
        if not linkedin_account and state:
            pending_nonce = request.env['ir.config_parameter'].sudo().get_param(
                'cyllo_linkedin.pending_new_account_nonce') or ''
            is_new_pending = bool(pending_nonce) and secrets.compare_digest(pending_nonce, state)
        if linkedin_account or is_new_pending:
            code = kw.get('code')
            if linkedin_account:
                linkedin_account.oauth_nonce = False
            else:
                request.env['ir.config_parameter'].sudo().set_param(
                    'cyllo_linkedin.pending_new_account_nonce', '')
            linkedin_auth_provider = request.env.ref('cyllo_linkedin.provider_linkedin')
            if not linkedin_auth_provider.client_id or not linkedin_auth_provider.client_secret:
                return request.make_response(
                    _('LinkedIn Provider credentials are missing. '
                      'Please fill in the Client ID and Client Secret in the OAuth Provider settings.'),
                    status=400
                )
            base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
            redirect_uri = url_join(base_url, '/linkedin/redirect')
            token_url = 'https://www.linkedin.com/oauth/v2/accessToken'
            token_data = {
                'grant_type': 'authorization_code',
                'code': code,
                'client_id': linkedin_auth_provider.client_id,
                'client_secret': linkedin_auth_provider.client_secret,
                'redirect_uri': redirect_uri,
            }
            try:
                token_response = requests.post(token_url, data=token_data, timeout=30).json()
                access_token = token_response.get('access_token')
            except Exception as e:
                return request.make_response(
                    _('Failed to connect to LinkedIn: %s') % str(e),
                    status=400
                )
            if not access_token:
                return request.make_response(
                    _('Failed to obtain access token. Response: %s') % token_response,
                    status=400
                )
            user_info_url = 'https://api.linkedin.com/v2/userinfo'
            headers = {'Authorization': f'Bearer {access_token}'}
            try:
                user_info_response = requests.get(user_info_url, headers=headers, timeout=30).json()
                profile_pic = user_info_response.get('picture')
            except Exception as e:
                return request.make_response(
                    _('Failed to fetch user info: %s') % str(e),
                    status=400
                )
            if linkedin_account:
                linkedin_account.write({
                    'linkedin_access_token': access_token,
                    'state': 'connected',
                    'linkedin_profile_image_url': profile_pic,
                    'name': user_info_response.get('name', linkedin_account.name or 'LinkedIn Account'),
                })
            else:
                linkedin_account = request.env['linkedin.account'].sudo().create({
                    'name': user_info_response.get('name', 'LinkedIn Account'),
                    'linkedin_access_token': access_token,
                    'state': 'connected',
                    'linkedin_profile_image_url': profile_pic,
                })
            linkedin_account.action_sync_organizations()
            try:
                menu_id = request.env.ref('cyllo_social_media_marketing.menu_cyllo_social_media_marketing_root').id
                action_id = request.env.ref("cyllo_social_media_marketing.social_media_dashboard_action").id
                url = f'/web#menu_id={menu_id}&action={action_id}'
            except Exception:
                url = '/web'
            return request.redirect(url)

        return super(LinkedInSocialController, self).social_linkedin_callbacks()
