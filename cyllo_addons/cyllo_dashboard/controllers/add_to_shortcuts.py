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
from odoo import http
from odoo.http import Controller, request, route


class AddToShortcuts(Controller):
    """Controller for managing user shortcuts."""

    @route('/add_to_shortcuts', type='json', auth='user')
    def add_to_shortcuts(self, actionId, name, model, menu_id):
        """
            Adds a specific action identified by 'actionId' from the user's shortcuts.
        """

        isMenu = request.env['ir.ui.menu'].sudo().search_count([
            ('action', 'like', f'ir.actions.act_window,{actionId}')
        ])
        try:
            if isinstance(menu_id, str):
                menu_id = int(menu_id.strip())
        except ValueError:
            return {'error': 'Invalid menu_id'}
        model_record = request.env['ir.model'].sudo().search(
            [('model', '=', model)], limit=1)
        if not model_record:
            return {'error': 'Model not found'}
        menu_record = request.env['ir.ui.menu'].sudo().browse(menu_id)
        if not menu_record.exists():
            return {'error': 'Menu not found'}
        path = menu_record.complete_name
        if isMenu > 0 and '/' in path:
            path = path.rsplit('/', 1)[0]
        request.env['shortcut.menu'].sudo().create({
            'name': name,
            'menu_id': menu_id,
            'window_action_id': actionId,
            'res_model': model_record.id,
            'path': path,
        })

        return True

    @route('/remove_from_shortcuts', type='json', auth='user')
    def remove_from_shortcuts(self, actionId):
        """
            Removes a specific action identified by 'actionId' from the user's
            shortcuts.

            Parameters: actionId (int): The ID of the action to be removed from
            the user's shortcuts.
        """
        request.env['shortcut.menu'].sudo().search(
            [('window_action_id', '=', actionId)]).unlink()
        return True

    @http.route('/get_idle_time/timer', auth='public', type='json')
    def get_idle_time(self):
        """
            Getting the idle time set inside res.user.
        """
        if request.env.user.idle_timer:
            return request.env.user.idle_time
