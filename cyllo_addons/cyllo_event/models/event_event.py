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


class EventEvent(models.Model):
    _inherit = 'event.event'

    @api.model_create_multi
    def create(self, vals_list):
        """Disable website menu and registration button during event creation."""
        for vals in vals_list:
            if 'website_menu' in vals:
                vals['website_menu'] = False
            if 'menu_register_cta' in vals:
                vals['menu_register_cta'] = False
        return super().create(vals_list)

    def write(self, vals):
        """Disable website menu and registration button during event update."""
        if 'website_menu' in vals:
            vals['website_menu'] = False
        if 'menu_register_cta' in vals:
            vals['menu_register_cta'] = False
        return super().write(vals)
