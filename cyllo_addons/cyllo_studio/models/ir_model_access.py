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
from odoo import api, models


class IrModelAccess(models.Model):
    _inherit = 'ir.model.access'

    @api.model
    def check(self, model, mode='read', raise_exception=True):
        """Override to bypass ACL errors when the user is inside a Cyllo Studio session.

        The bypass is intentionally broad (all modes) because Studio users need
        to be able to read, write and create records in every module they open
        inside the editor.  The bypass is session-scoped only:
          - request.session.studio == '1'  →  user actively opened Studio
          - group_cyllo_studio_user        →  user has a Studio licence

        Non-Studio users are never affected: ir_http.py ensures that only
        members of group_cyllo_studio_user can ever set session.studio = '1'.
        """
        try:
            from odoo.http import request  # noqa: PLC0415 – local import avoids circular deps
            studio = getattr(request.session, 'studio', None)
            in_studio = bool(studio) and '1' in studio
        except RuntimeError:
            # No active HTTP request (e.g. cron job / shell) — behave normally.
            in_studio = False

        if in_studio and self.env.user.has_group('cyllo_studio.group_cyllo_studio_user'):
            # Grant access silently — Studio users should never hit an access wall
            # while exploring or editing any module inside the Studio editor.
            return True

        return super().check(model, mode=mode, raise_exception=raise_exception)

    def update_access_rights(self, access_rights_data):
        """Update access rights for matching records."""
        for access in self:
            access_right = next((access_data for access_data in access_rights_data if access_data.get('id') == access.id), None)
            if access_right:
                access.update({
                    'name': access_right['name'],
                    'group_id': access_right['group_id'][0],
                    'perm_read': access_right['perm_read'],
                    'perm_write': access_right['perm_write'],
                    'perm_create': access_right['perm_create'],
                    'perm_unlink': access_right['perm_unlink']
                })