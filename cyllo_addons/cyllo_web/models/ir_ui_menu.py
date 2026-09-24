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
from odoo.http import request


class IrUiMenu(models.Model):
    """Inherits ir.ui.menu to pass value to js."""
    _inherit = 'ir.ui.menu'

    @api.model
    def get_menu(self):
        """When action not equals None, models are searched using search_read()
        and the list is retrieved."""
        menu_ids = list(self._visible_menu_ids(request.session.debug if request else False))
        if request.session.debug == '1':
            domain = [('action', '!=', None), ('id', 'in', menu_ids)]
        else:
            domain = [('action', '!=', None), ('id', 'in', menu_ids), ('groups_id', '!=', False)]
        search = self.search_read(domain, ['complete_name', 'name', 'groups_id'])
        return search
