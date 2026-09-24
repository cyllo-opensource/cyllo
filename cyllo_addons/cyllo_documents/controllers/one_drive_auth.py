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
import json

from odoo import http
from odoo.http import request


class OneDriveAuth(http.Controller):
    """Controller for handling OneDrive authentication."""
    @http.route('/one_drive/auth', type='http', auth="public")
    def oauth2callback(self, **kw):
        """Callback function for OneDrive authentication.
        param kw: A dictionary of keyword arguments.
        return: A redirect response."""
        state = json.loads(kw['state'])
        one_drive_connector = request.env['one.drive.connector'].sudo().browse(state.get('one_drive_connector_id'))
        one_drive_connector.get_onedrive_tokens(kw.get('code'))
        return request.redirect(state.get('url_return'))
