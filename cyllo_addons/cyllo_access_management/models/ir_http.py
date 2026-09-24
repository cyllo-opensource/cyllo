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
import re
import odoo
from odoo import models
from odoo.exceptions import AccessDenied
from odoo.http import request

class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _authenticate(cls, endpoint):
        """
        Force immediate logout if the user's login is blocked.
        This occurs on every request that requires authentication.
        """
        super()._authenticate(endpoint)

        if request.session.uid and endpoint.routing.get('auth') != 'none':
            try:
                user = request.env.user.sudo()
                if hasattr(user, '_check_profile_management'):
                    user._check_profile_management()
            except AccessDenied:
                request.session.logout(keep_db=True)

    @classmethod
    def _handle_debug(cls):
        """Disable debug mode based on profile management restrictions."""
        super()._handle_debug()
        if not getattr(request.session, 'debug', False):
            return
        if not request.db or not getattr(request.session, 'uid', False):
            return
        try:
            cids_raw = request.httprequest.args.get('cids') or request.httprequest.cookies.get('cids')
            active_company_ids = []
            if cids_raw:
                try:
                    for part in re.split(r'[,-]', str(cids_raw)):
                        if part.strip().isdigit():
                            active_company_ids.append(int(part.strip()))
                except Exception:
                    pass

            with request.env.registry.cursor() as cr:
                env = odoo.api.Environment(cr, request.session.uid, request.session.context)
                user = env.user
                if not active_company_ids:
                    active_company_ids = [env.company.id]
                if user.sudo().profile_ids and not (user.has_group('base.group_system') or user.has_group('base.group_erp_manager')):
                    access_mgmt = env['profile.management'].sudo().search([
                        ('profile_ids', 'in', user.sudo().profile_ids.ids),
                        ('is_activated', '=', True),
                        ('disable_debug_mode', '=', True),
                        "|",
                        ('company_ids', '=', False),
                        ('company_ids', 'in', active_company_ids)
                    ], limit=1)
                    if access_mgmt:
                        request.session.debug = ""
                        request.session.debug_denied = True
        except Exception:
            pass

    def session_info(self):
        """ Add debug_denied flag to session_info so the web client can show a notification. """
        res = super(IrHttp, self).session_info()
        if hasattr(request, 'session'):
            res['debug_denied'] = getattr(request.session, 'debug_denied', False)
            if res.get('debug_denied'):
                request.session.debug_denied = False
            user = request.env.user
            profiles = user.sudo().profile_ids
            company_id = request.env.company.id
            is_readonly = False
            if profiles and not (user.has_group('base.group_system') or user.has_group('base.group_erp_manager')):
                access_mgmt = request.env['profile.management'].sudo().search([
                    ('profile_ids', 'in', profiles.ids),
                    ('is_activated', '=', True),
                    ('is_readonly', '=', True),
                    "|",
                    ('company_ids', 'in', [company_id]),
                    ('company_ids', '=', False)
                ], limit=1)
                if access_mgmt:
                    is_readonly = True
                    user.toggle_auto_edit(False)
            res['is_profile_readonly'] = is_readonly
        return res
