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


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    def session_info(self):
        res = super(IrHttp, self).session_info()
        recent_app = self.env['recent.apps'].sudo()
        pinned_menu = self.env['pinned.menu'].sudo()
        res['is_auto_edit'] = self.env.user.auto_edit
        res['recent_app'] = recent_app.search_read([
            ('user_id', '=', self.env.uid)], ["app_id", "name"],
            order="create_date DESC")
        res['pinned_menu'] = pinned_menu.search_read([
            ('user_id', '=', self.env.uid)], ["app_id", "name"],
            order="create_date DESC")
        return res
