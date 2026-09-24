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


class RestaurantTable(models.Model):
    _inherit = 'restaurant.table'

    appointment_resource_id = fields.Many2one(
        'appointment.resource',
        string='Appointment Resource',
        index='btree_not_null',
        ondelete='set null',
    )

    def _get_appointment_resource_name(self):
        self.ensure_one()
        seats = self.seats or 0
        unit = 'seat' if seats == 1 else 'seats'
        return f'{self.floor_id.name} Table {self.name} (\U0001FA91 {seats} {unit})'

    @api.model_create_multi
    def create(self, vals_list):
        tables = super().create(vals_list)
        for table in tables:
            if not table.appointment_resource_id:
                resource = self.env['appointment.resource'].sudo().create({
                    'name': table._get_appointment_resource_name(),
                    'capacity': table.seats,
                    'resource_type': 'room',
                    'pos_table_ids': [table.id],
                })
                table.appointment_resource_id = resource
        return tables

    def write(self, vals):
        res = super().write(vals)
        if 'active' in vals:
            for table in self:
                if not table.appointment_resource_id:
                    continue
                if not vals['active']:
                    table.appointment_resource_id.sudo().active = False
                else:
                    table.appointment_resource_id.sudo().write({
                        'name': table._get_appointment_resource_name(),
                        'capacity': table.seats,
                    })
        elif {'seats', 'name'} & vals.keys():
            for table in self:
                if table.appointment_resource_id:
                    table.appointment_resource_id.sudo().write({
                        'name': table._get_appointment_resource_name(),
                        'capacity': table.seats,
                    })
        return res

    def unlink(self):
        for table in self:
            table.appointment_resource_id.sudo().unlink()
        return super().unlink()

    @api.ondelete(at_uninstall=True)
    def _delete_linked_resources(self):
        for table in self:
            if table.appointment_resource_id:
                table.appointment_resource_id.unlink()
