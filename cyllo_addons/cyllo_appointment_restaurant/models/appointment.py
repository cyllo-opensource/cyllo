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
from datetime import timedelta

from odoo import api, fields, models


class Appointment(models.Model):
    _inherit = 'appointment.appointment'

    @api.model
    def _send_table_notifications(self, appointments, command):
        """
        Notify all active POS sessions whose tables are involved in the
        given appointments with a TABLE_BOOKING websocket message.

        :param appointments: appointment.appointment recordset
        :param command: 'ADDED' or 'REMOVED'
        """
        now = fields.Datetime.now()
        window_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        window_end = window_start + timedelta(days=7)

        for appointment in appointments:
            resource = appointment.resource_id
            if not resource:
                continue
            tables = resource.pos_table_ids
            if not tables:
                continue
            # Skip appointments outside the POS session's 7-day window.
            if appointment.start_datetime and not (
                window_start <= appointment.start_datetime < window_end
            ):
                continue
            appointment_dict = {
                'id': appointment.id,
                'name': appointment.display_name or appointment.name,
                'start_datetime': (
                    appointment.start_datetime.strftime('%Y-%m-%d %H:%M:%S')
                    if appointment.start_datetime else False
                ),
                'end_datetime': (
                    appointment.end_datetime.strftime('%Y-%m-%d %H:%M:%S')
                    if appointment.end_datetime else False
                ),
                'resource_id': resource.id,
                'partner_id': appointment.partner_id.id,
                'attendee_count': appointment.attendee_count or 1,
                'state': appointment.state,
            }
            for table in tables:
                for config in table.floor_id.pos_config_ids:
                    session = config.current_session_id
                    if not session:
                        continue
                    self.env['bus.bus']._sendone(
                        f'pos_session-{session.id}',
                        'TABLE_BOOKING',
                        {
                            'command': command,
                            'event': appointment_dict,
                        },
                    )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        self._send_table_notifications(records, 'ADDED')
        return records

    def write(self, vals):
        self._send_table_notifications(self, 'REMOVED')
        result = super().write(vals)
        self._send_table_notifications(self, 'ADDED')
        return result

    def unlink(self):
        self._send_table_notifications(self, 'REMOVED')
        return super().unlink()

    def action_check_in(self):
        self.ensure_one()
        self.sudo().write({
            'state': 'in_progress',
        })

        return True
