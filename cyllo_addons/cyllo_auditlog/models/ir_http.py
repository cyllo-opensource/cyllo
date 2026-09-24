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
from odoo import models
from odoo.http import request


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _authenticate(cls, endpoint):
        """
        Capture session on successful authentication/capture for all interactive requests
        if session tracking is enabled, and log the HTTP request.
        """
        res = super()._authenticate(endpoint)
        if request and request.uid and getattr(request.session, 'uid', False) == request.uid:
            # ONLY create a brand new session exactly during the explicit login routing Phase.
            # This completely bypasses the 20+ concurrent asset loads directly following a login and prevents duplicates!
            allowed_paths = ['/web/session/authenticate', '/web/login']
            if getattr(request, 'httprequest', False) and request.httprequest.path in allowed_paths:
                if request.env['audit.rule'].sudo().search_count([('active', '=', True), ('track_session', '=', True)]):
                    request.env['audit.session'].sudo().get_or_create_session()
        return res
