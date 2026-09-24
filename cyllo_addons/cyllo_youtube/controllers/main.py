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
from odoo import http
from odoo.http import request


class YouTubeAuthorizationController(http.Controller):
    """
        Controller for handling YouTube authorization callbacks.
        """

    @http.route('/odoo_youtube', type='http', auth='public', website=True)
    def youtube_auth_callback(self, **kwargs):
        """
            Callback function for handling YouTube authorization.
        """
        account = request.env['youtube.account'].sudo().search(
            [('oauth_nonce', '=', kwargs.get('state'))], limit=1) if kwargs.get('state') else None
        if not account:
            return request.make_response('Invalid or expired OAuth state.', status=400)
        account.oauth_nonce = False

        authorization_code = kwargs.get('code')
        if authorization_code:
            account.authenticate_with_youtube(authorization_code)

        base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
        action_id = request.env.ref('cyllo_youtube.action_view_youtube_account').id
        redirect_url = base_url + '/web#id=%d&action=%d&view_type=form&model=youtube.account' % (
            account.id, action_id)
        return request.redirect(redirect_url)
