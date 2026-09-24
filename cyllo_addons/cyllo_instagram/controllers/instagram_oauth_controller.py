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
from dateutil.relativedelta import relativedelta

from odoo import fields, http, _
from odoo.http import request
from werkzeug.urls import url_join


class InstagramOAuthController(http.Controller):
    """Controller handling the Instagram (Facebook) OAuth connect callback."""

    @http.route('/instagram/oauth/callback', type='http', auth='public', csrf=False)
    def instagram_oauth_callback(self, **kw):
        state = kw.get('state') or ''
        account = request.env['social.insta.account'].sudo().search(
            [('oauth_nonce', '=', state)], limit=1) if state else request.env['social.insta.account']
        if not account:
            return request.make_response(_('Invalid or expired OAuth state.'), status=400)
        account.oauth_nonce = False

        redirect_url = f'/web#model=social.insta.account&id={account.id}&view_type=form'

        if kw.get('error'):
            account._message_log(body=_('Facebook OAuth connection was cancelled: %s') % kw.get('error'))
            return request.redirect(redirect_url)

        code = kw.get('code')
        if not code:
            return request.make_response(_('Missing authorization code from Facebook.'), status=400)

        try:
            base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
            redirect_uri = url_join(base_url, '/instagram/oauth/callback')

            token_url = f'{account.instagram_base_url}/oauth/access_token'
            token_response = requests.get(token_url, params={
                'client_id': account.meta_app_number,
                'client_secret': account.meta_app_secret,
                'redirect_uri': redirect_uri,
                'code': code,
            }, timeout=30).json()
            short_lived_token = token_response.get('access_token')
            if not short_lived_token:
                account._message_log(
                    body=_('Facebook OAuth failed: %s') % token_response.get('error', token_response)
                )
                return request.redirect(redirect_url)

            exchange_response = requests.get(token_url, params={
                'grant_type': 'fb_exchange_token',
                'client_id': account.meta_app_number,
                'client_secret': account.meta_app_secret,
                'fb_exchange_token': short_lived_token,
            }, timeout=30).json()
            long_lived_token = exchange_response.get('access_token') or short_lived_token

            accounts_url = f'{account.instagram_base_url}/me/accounts'
            accounts_response = requests.get(accounts_url, params={'access_token': long_lived_token}, timeout=30).json()
            if accounts_response.get('error'):
                account._message_log(
                    body=_('Facebook OAuth failed: %s') % accounts_response['error'].get('message')
                )
                return request.redirect(redirect_url)

            page = next(
                (p for p in accounts_response.get('data', []) if p.get('name') == account.facebook_insta_page_name),
                None,
            )
            if not page:
                account._message_log(body=_('Page not found with given name via OAuth'))
                return request.redirect(redirect_url)

            page_access_token = page.get('access_token')
            business_url = f"{account.instagram_base_url}/{page['id']}"
            business_response = requests.get(business_url, params={
                'fields': 'id,name,instagram_business_account',
                'access_token': page_access_token,
            }, timeout=30).json()
            instagram_business_account = business_response.get('instagram_business_account')
            if not instagram_business_account:
                account._message_log(body=_('No Instagram Business Account linked to this Facebook Page'))
                return request.redirect(redirect_url)

            insta_url = f"{account.instagram_base_url}/{page['id']}/instagram_accounts"
            insta_response = requests.get(insta_url, params={
                'access_token': page_access_token,
                'fields': 'id,username,profile_pic',
            }, timeout=30).json()
            insta_data = insta_response.get('data') or [{}]

            account.write({
                'instagram_access_token': long_lived_token,
                'facebook_insta_page_number': page['id'],
                'instagram_page_access_token': page_access_token,
                'instagram_business_account_number': instagram_business_account['id'],
                'instagram_account_number': insta_data[0].get('id'),
                'renewal_date': fields.Date.today() + relativedelta(days=50),
                'state': 'connected',
                'instagram_connection_authenticated': True,
            })
            account._message_log(body=_('Connected via Facebook OAuth'))
            account.action_fetch_audience()
            request.env['ir.config_parameter'].sudo().set_param(
                'social_insta_account.default_insta_account_id', account.id
            )
        except Exception as exc:
            account._message_log(body=_('Facebook OAuth connection failed: %s') % str(exc))

        return request.redirect(redirect_url)
