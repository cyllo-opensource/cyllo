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

from odoo.addons.web.controllers.home import Home

class ExtendedHome(Home):

    @http.route('/web', type='http', auth="none")
    def web_client(self, s_action=None, **kw):
        """
            Overrides the default web client route to handle the 'studio' query parameter.

            This method checks for the 'studio' parameter in the URL and, if present, verifies if the user belongs to
            the 'base.group_erp_manager' group before enabling or disabling studio mode in the user's session.

            Parameters:
                s_action (str, optional): The ID of the action to execute. Defaults to None.
                **kw (dict): Additional keyword arguments.

            Returns:
                http.Response: The response from the parent class's `web_client` method.
            """
        studio = request.httprequest.args.get('studio', '0')
        if studio is not None:
            user = request.env.user.browse(request.session.uid)
            if not user.has_group('cyllo_studio.group_cyllo_studio_user'):
                studio = '0'
            request.session.studio = studio if studio == '1' else None
        else:
            request.session.studio = None

        return super().web_client(s_action=s_action, **kw)
