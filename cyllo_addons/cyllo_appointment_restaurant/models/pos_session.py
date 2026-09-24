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
from datetime import timedelta


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _pos_ui_models_to_load(self):
        models = super()._pos_ui_models_to_load()
        if self.config_id.module_pos_restaurant:
            if 'appointment.resource' not in models:
                models += ['appointment.resource']
            if 'appointment.appointment' not in models:
                models += ['appointment.appointment']
        return models

    def _loader_params_restaurant_table(self):
        params = super()._loader_params_restaurant_table()
        field_list = params['search_params']['fields']
        if 'appointment_resource_id' not in field_list:
            field_list.append('appointment_resource_id')
        return params

    def _loader_params_appointment_resource(self):
        return {
            'search_params': {
                'domain': [],
                'fields': ['id', 'name', 'capacity', 'pos_table_ids'],
            }
        }

    def _get_pos_ui_appointment_resource(self, params):
        return self.env['appointment.resource'].search_read(
            **params['search_params']
        )

    def _loader_params_appointment_appointment(self):
        now = fields.Datetime.now()
        window_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        window_end = window_start + timedelta(days=7)
        domain = [
            ('start_datetime', '>=', window_start),
            ('start_datetime', '<', window_end),
            ('state', 'not in', ['draft','cancelled', 'no_show', 'done']),
        ]
        pos_table_resource_ids = self.env['appointment.resource'].search([
            ('pos_table_ids', '!=', False),
        ]).ids
        if pos_table_resource_ids:
            domain.append(('resource_id', 'in', pos_table_resource_ids))
        return {
            'search_params': {
                'domain': domain,
                'fields': [
                    'id', 'name', 'display_name',
                    'start_datetime', 'end_datetime', 'duration',
                    'resource_id', 'partner_id',
                    'attendee_count', 'state',
                ],
            }
        }

    def _get_pos_ui_appointment_appointment(self, params):
        return self.env['appointment.appointment'].search_read(
            **params['search_params']
        )