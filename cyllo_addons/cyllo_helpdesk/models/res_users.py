# -*- coding: utf-8 -*-
#############################################################################
#
#    Cyllo Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cyllo(<https://www.cyllo.com>)
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


class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.model
    def default_get(self, fields):
        """Set Helpdesk Manager as default group for new users."""
        res = super().default_get(fields)
        manager_group = self.env.ref('cyllo_helpdesk.cyllo_helpdesk_manager',
                                     raise_if_not_found=False)
        if manager_group and 'groups_id' in fields:
            groups_id = res.get('groups_id', [])
            groups_id.append((4, manager_group.id))
            res['groups_id'] = groups_id
        return res

    @api.model
    def _init_cyllo_helpdesk_groups(self):
        """Assign Helpdesk Manager group to all existing internal users."""
        manager_group = self.env.ref('cyllo_helpdesk.cyllo_helpdesk_manager',
                                     raise_if_not_found=False)
        if manager_group:
            internal_users = self.search([('share', '=', False)])
            for user in internal_users:
                if not user.has_group('cyllo_helpdesk.cyllo_helpdesk_manager'):
                    user.write({'groups_id': [(4, manager_group.id)]})
