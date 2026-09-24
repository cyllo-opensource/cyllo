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
from lxml import etree

from odoo import api, fields, models


class AddToShortcut(models.Model):
    _name = 'shortcut.menu'
    _description = 'Shortcut Menus'

    name = fields.Char('Name')
    res_model = fields.Many2one('ir.model', 'Model')
    window_action_id = fields.Many2one('ir.actions.act_window')
    client_action_id = fields.Many2one('ir.actions.client')
    server_action_id = fields.Many2one('ir.actions.server')
    menu_id = fields.Many2one('ir.ui.menu')
    xml_id = fields.Char(
        string='External ID', related='window_action_id.xml_id', store=True)
    model = fields.Char(related='window_action_id.res_model')
    path = fields.Char('Path')
    view_type = fields.Char('View Type')
    xml_can_create = fields.Boolean(string='XML Can Create', default=False)
    can_create = fields.Boolean(
        compute='_compute_can_create',
        string='Can Create',
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            window_action_id = vals.get('window_action_id')
            if window_action_id:
                action = self.env['ir.actions.act_window'].browse(window_action_id)
                vals['xml_can_create'] = self._is_model_create_allowed(action)
        return super().create(vals_list)

    @api.depends_context('uid')
    @api.depends('xml_can_create', 'model')
    def _compute_can_create(self):
        for record in self:
            record.can_create = False
            if not record.xml_can_create or not record.model:
                continue
            try:
                model_obj = self.env[record.model]
                if not model_obj.check_access_rights('create', raise_exception=False):
                    continue
            except KeyError:
                continue
            record.can_create = True

    def _is_model_create_allowed(self, action):
        if not action or not action.res_model:
            return False
        view_type = False
        view_id = False
        if action.views:
            for resolved_view_id, resolved_view_type in action.views:
                if resolved_view_type in ('tree', 'form', 'kanban'):
                    view_type = resolved_view_type
                    view_id = resolved_view_id
                    break
        if not view_type:
            view_type = (action.view_mode.split(',')[0].strip() if action.view_mode else 'tree') or 'tree'
        if view_type not in ('tree', 'form', 'kanban'):
            return False

        if not view_id and not action.view_id:
            view = self.env["ir.ui.view"].search(
                [
                    ("model", "=", action.res_model),
                    ("type", "=", view_type),
                ],
                order="priority,id",
                limit=1,
            )
            if view:
                view_id = view.id if view.id else False

        try:
            view_data = self.env['ir.ui.view'].get_view(
                view_id=action.view_id.id or view_id,
                view_type=view_type,
            )
            arch = etree.fromstring(view_data['arch'])
        except Exception:
            return False

        create_attr = arch.get('create')
        if create_attr in ('0', 'false', 'False'):
            return False

        return True
