# -*- coding: utf-8 -*-
#############################################################################
#
#    Cyllo Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cyllo(<https://www.cyllo.com>)
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
from odoo import models, fields, api


class AppointmentType(models.Model):
    _inherit = 'appointment.type'

    station_id = fields.Many2one(
        'frontdesk.frontdesk',
        string='Default Front Desk Station',
        help='Default front desk station assigned to appointments of this type.'
    )


class Appointment(models.Model):
    _inherit = 'appointment.appointment'

    station_id = fields.Many2one(
        'frontdesk.frontdesk',
        string='Front Desk Station',
        help='Front desk station assigned to this appointment.'
    )
    visitor_id = fields.Many2one(
        'frontdesk.visitor',
        string='Source Visitor',
        help='Visitor for whom this appointment was booked.'
    )

    @api.onchange('appointment_type_id')
    def _onchange_appointment_type_id_station(self):
        """Automatically set the front desk station based on the selected appointment type."""
        if self.appointment_type_id and self.appointment_type_id.station_id:
            self.station_id = self.appointment_type_id.station_id

    def write(self, vals):
        """Synchronize appointment state changes with front desk visitors."""
        started_appointments, done_appointments, cancelled_appointments = False, False, False
        res = super().write(vals)

        if vals.get('state') == 'in_progress':
            started_appointments = self.filtered(lambda a: a.state == 'in_progress')

        if vals.get('state') == 'done':
            done_appointments = self.filtered(lambda a: a.state == 'done')

        if vals.get('state') == 'cancelled':
            cancelled_appointments = self.filtered(lambda a: a.state == 'cancelled')

        if started_appointments:
            visitors_to_check_in = self.env['frontdesk.visitor'].search([
                ('appointment_id', 'in', started_appointments.ids),
                ('state', '=', 'planned')
            ])
            if visitors_to_check_in:
                visitors_to_check_in.action_check_in()

        if done_appointments:
            visitors_to_check_out = self.env['frontdesk.visitor'].search([
                ('appointment_id', 'in', done_appointments.ids),
                ('state', '=', 'checked_in')
            ])
            if visitors_to_check_out:
                visitors_to_check_out.action_check_out()

        if cancelled_appointments:
            visitors_to_cancel = self.env['frontdesk.visitor'].search([
                ('appointment_id', 'in', cancelled_appointments.ids),
                ('state', 'not in', ('cancelled', 'checked_out'))
            ])
            if visitors_to_cancel:
                visitors_to_cancel.action_cancel()

        return res

    @api.model_create_multi
    def create(self, vals_list):
        """Create appointments and initialize front desk integration data."""
        records = super().create(vals_list)
        # Link visitor if appointment was created via the quick book action
        for record in records:
            if record.visitor_id:
                record.visitor_id.write({'appointment_id': record.id})
            if record.station_id or record.appointment_type_id.station_id:
                record._create_frontdesk_visitors()
        return records

    def _create_frontdesk_visitors(self):
        """Create visitor records for appointments."""
        visitor_vals = []
        for appt in self:
            # Skip if this appointment already has a visitor linked
            if appt.visitor_id:
                continue
            station = appt.station_id or appt.appointment_type_id.station_id
            if station:
                visitor_vals.append({
                    'name': appt.partner_id.name or 'Visitor',
                    'host_id': appt.staff_id.id if appt.staff_id else False,
                    'expected_arrival': appt.start_datetime,
                    'station_id': station.id,
                    'state': 'planned',
                    'appointment_id': appt.id,
                    'email': appt.partner_id.email,
                    'phone': appt.partner_id.phone or appt.partner_id.mobile,
                    'company': appt.partner_id.parent_id.name or appt.partner_id.company_name,
                    'partner_id': appt.partner_id.id,
                    'visitor_name': appt.partner_id.name or 'Visitor',
                })
        if visitor_vals:
            self.env['frontdesk.visitor'].create(visitor_vals)
