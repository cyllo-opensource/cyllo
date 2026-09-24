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
from odoo import fields, models, api
from odoo.exceptions import AccessDenied
from odoo.http import request


class ResUsers(models.Model):
    _inherit = "res.users"

    profile_ids = fields.Many2many(
        'user.profile',
        string='Profiles',
        help="User access profiles assigned to this user."
    )

    @classmethod
    def authenticate(cls, db, login, password, user_agent_env):
        """Authenticate the user and validate profile access rules."""
        uid = super().authenticate(db, login, password, user_agent_env)
        if uid:
            with cls.pool.cursor() as cr:
                env = api.Environment(cr, uid, {})
                user = env.user
                user._check_profile_management()

        return uid

    def write(self, vals):
        """Synchronize user groups when profile assignments are updated."""
        previous_group_ids = self.profile_ids.group_ids.filtered(lambda x:
                                                                 x.id != 1)
        res = super().write(vals)
        if 'profile_ids' in vals:
            current_group_ids = self.profile_ids.group_ids.filtered(lambda x:
                                                                    x.id != 1)

            remove_group_ids = previous_group_ids - current_group_ids
            add_group_ids = current_group_ids - previous_group_ids
            commands = []
            if add_group_ids:
                for group in add_group_ids:
                    commands.append(fields.Command.link(group.id))
            if remove_group_ids:
                for group in remove_group_ids:
                    commands.append(fields.Command.unlink(group.id))
            if commands:
                self.write({"groups_id": commands})
        return res

    def _check_profile_management(self):
        """Validate whether login is blocked by profile management."""
        if self.has_group('base.group_system') or self.has_group('base.group_erp_manager'):
            return
        access_count = self.env['profile.management'].sudo().search_count([
            ('profile_ids', 'in', self.sudo().profile_ids.ids),
            ('is_activated', '=', True),
            ('disable_login', '=', True)
        ])
        if access_count:
            if request:
                request.session['profile_access_denied'] = True
            raise AccessDenied()