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


class IrModel(models.Model):
    _inherit = 'ir.model'

    list_split_view = fields.Boolean(help="Field to split views")
    master_search = fields.Boolean(
        help="Enable this to include the model in the master search.")

    def unlink(self):
        super(IrModel, self).unlink()
        recent_apps = self.env['recent.apps']
        for record in recent_apps.search([]).mapped('app_id'):
            if record not in self.env['ir.ui.menu'].search(
                    [('active', '=', True)]).mapped('id'):
                recent_apps.search([('app_id', '=', record)]).unlink()
        return

    @api.model
    def add_split_view(self, rec):
        """
        Update the 'list_split_view' field to True for the given model.
        :param rec: The model to update.
        """
        self.sudo().search([('model', '=', rec)]).write({
            'list_split_view': True
        })

    @api.model
    def remove_split_view(self, rec):
        """
        Update the 'list_split_view' field to False for the given model.
        :param rec: The model to update.
        """
        self.sudo().search([('model', '=', rec)]).write({
            'list_split_view': False
        })

    @api.model
    def get_split_view_mode(self, model_name):
        """Returns the list_split_view mode for the given model with sudo()"""
        return self.sudo().search_read(
            [('model', '=', model_name)], ["list_split_view"])
