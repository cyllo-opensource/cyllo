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
from odoo import api, fields, models


class PinnedMenu(models.Model):
    _name = 'pinned.menu'
    _description = 'Pinned Menu'

    name = fields.Char(compute='_compute_name', store=True)
    app_id = fields.Integer()
    user_id = fields.Many2one('res.users')

    @api.depends('app_id')
    def _compute_name(self):
        menu_ui = self.env['ir.ui.menu']
        for rec in self:
            app = menu_ui.browse(rec.app_id)
            rec.name = app.name

    @api.model
    def unpin_menu(self, app_id):
        self.search([
            ("app_id", "=", app_id), ("user_id", "=", self.env.uid)
        ]).unlink()
