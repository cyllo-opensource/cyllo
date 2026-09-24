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


class RecentApps(models.Model):
    _name = 'recent.apps'
    _inherit = 'pinned.menu'
    _description = 'Recent Apps'

    @api.model
    def create(self, val_list):
        rec_ids = self.search([("user_id", "=", val_list["user_id"])],
                              order="create_date DESC")
        if val_list["app_id"] in rec_ids.mapped("app_id"):
            rec_ids.browse(val_list["app_id"]).unlink()
        res = super(RecentApps, self).create(val_list)
        if len(rec_ids) > 4:
            rec_ids[4:].unlink()
        return res
