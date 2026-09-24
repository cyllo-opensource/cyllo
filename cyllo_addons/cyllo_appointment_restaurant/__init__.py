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
from . import models


def _cyllo_appointment_restaurant_after_init(env):
    """
    After module installation, create an appointment.resource for every
    restaurant.table that does not yet have one linked.
    """
    table_ids = env['restaurant.table'].search(
        [('appointment_resource_id', '=', False)]
    )
    for table in table_ids:
        table.appointment_resource_id = (
            env['appointment.resource'].sudo().create({
                'name': table._get_appointment_resource_name(),
                'capacity': table.seats,
                'resource_type': 'room',
                'pos_table_ids': [table.id],
            })
        )

    appt_type = env.ref('cyllo_appointment_restaurant.appointment_type_table', raise_if_not_found=False)
    if appt_type:
        all_tables = env['restaurant.table'].search([])
        resource_ids = all_tables.mapped('appointment_resource_id')
        if resource_ids:
            appt_type.sudo().write({'resource_ids': [(4, r.id) for r in resource_ids]})
