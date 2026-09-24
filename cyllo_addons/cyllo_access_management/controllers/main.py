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
from odoo.addons.web.controllers.home import Home
from odoo.http import request

class LoginPage(Home):

    @http.route('/web/login', type='http', auth='none')
    def web_login(self, redirect=None, **kw):
        """Handle profile-based login restriction errors."""
        response = super().web_login(redirect=redirect, **kw)
        if request.session.pop('profile_access_denied', False):
            response.qcontext['profile_error'] = (
                "Your login is blocked by the administrator. Please contact the Administrator"
            )
            response.qcontext.pop('error', None)
        return response