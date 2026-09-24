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

class IrUiMenu(models.Model):
    _inherit = "ir.ui.menu"

    def _load_menus_blacklist(self):
        """Extend the menu blacklist with menus hidden by profile management."""
        res = super()._load_menus_blacklist()
        user = self.env.user
        profiles = user.sudo().profile_ids
        company_id = self.env.company.id
        if not profiles or user.has_group('base.group_system') or user.has_group('base.group_erp_manager'):
            return res
        access_mgmt = self.env['profile.management'].sudo().search([
            ('profile_ids', 'in', profiles.ids), ('is_activated', '=', True),
            "|",
            ('company_ids', 'in', [company_id]), ('company_ids', '=', False)
        ])
        menus_to_hide = access_mgmt.menu_ids
        if menus_to_hide:
            res.extend(menus_to_hide.ids)
        return res
