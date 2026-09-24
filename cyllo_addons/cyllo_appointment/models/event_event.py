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
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import timedelta, datetime, time
import pytz

class EventEvent(models.Model):
    _inherit = 'event.event'

    requires_appointment = fields.Boolean(
        string='Requires Appointments', default=False,
        help='If checked, you can generate appointment slots for this event.'
    )
    appointment_type_id = fields.Many2one(
        'appointment.type', string='Appointment Type',
        domain="[('scheduling_type', '=', 'predefined')]",
        help='The appointment type used for generating slots.'
    )
    appointment_staff_ids = fields.Many2many(
        'hr.employee', 'event_event_hr_employee_rel', 'event_id', 'employee_id',
        string='Appointment Staff',
        help='Staff members who will take appointments during this event.'
    )
    appointment_slot_ids = fields.One2many(
        'appointment.slot', 'event_id', string='Appointment Slots'
    )
    appointment_count = fields.Integer(
        string='Appointments', compute='_compute_appointment_count'
    )

    @api.depends('appointment_slot_ids.appointment_ids')
    def _compute_appointment_count(self):
        for event in self:
            count = 0
            for slot in event.appointment_slot_ids:
                count += len(slot.appointment_ids.filtered(lambda a: a.state not in ('draft', 'cancelled', 'rejected')))
            event.appointment_count = count

    def action_generate_appointment_slots(self):
        self.ensure_one()
        if not self.requires_appointment:
            raise UserError(_("Please enable 'Requires Appointments' to generate slots."))
        if not self.appointment_type_id:
            raise UserError(_("Please select an Appointment Type."))
        if not self.appointment_staff_ids:
            raise UserError(_("Please select at least one Staff member."))
        if not self.date_begin or not self.date_end:
            raise UserError(_("Please set the Event's start and end dates first."))

        slot_interval_minutes = int(self.appointment_type_id.slot_interval)
        duration_hours = self.appointment_type_id.duration
        empty_slots = self.appointment_slot_ids.filtered(lambda s: s.booked_count == 0)
        empty_slots.unlink()
        event_start_utc = self.date_begin
        event_end_utc = self.date_end
        new_slots = []
        for staff in self.appointment_staff_ids:
            calendar = staff.resource_calendar_id
            tz_name = calendar.tz if calendar else 'UTC'
            staff_tz = pytz.timezone(tz_name)
            # Iterate each calendar day covered by the event (in staff timezone)
            event_start_local = pytz.utc.localize(event_start_utc).astimezone(staff_tz)
            event_end_local = pytz.utc.localize(event_end_utc).astimezone(staff_tz)
            current_day = event_start_local.date()
            end_day = event_end_local.date()
            while current_day <= end_day:
                weekday = str(current_day.weekday())
                if calendar:
                    attendances = calendar.attendance_ids.filtered(
                        lambda a: a.dayofweek == weekday
                    )
                else:
                    # No calendar: default 9–17
                    class FakeAtt:
                        hour_from = 9.0
                        hour_to = 17.0
                    attendances = [FakeAtt()]

                for att in attendances:
                    h_from, m_from = divmod(int(att.hour_from * 60), 60)
                    h_to, m_to = divmod(int(att.hour_to * 60), 60)
                    # Build window start/end in staff local time, then convert to UTC
                    window_start_local = staff_tz.localize(
                        datetime.combine(current_day, time(h_from, m_from))
                    )
                    window_end_local = staff_tz.localize(
                        datetime.combine(current_day, time(h_to, m_to))
                    )
                    event_start_aware = pytz.utc.localize(event_start_utc)
                    event_end_aware = pytz.utc.localize(event_end_utc)
                    window_start = max(window_start_local, event_start_aware)
                    window_end = min(window_end_local, event_end_aware)
                    if window_start >= window_end:
                        continue
                    # Generate slots within this window
                    slot_start = window_start
                    while slot_start + timedelta(hours=duration_hours) <= window_end:
                        slot_end = slot_start + timedelta(hours=duration_hours)
                        start_utc = slot_start.astimezone(pytz.utc).replace(tzinfo=None)
                        end_utc = slot_end.astimezone(pytz.utc).replace(tzinfo=None)
                        # Skip if already exists (e.g. booked from previous generation)
                        existing = self.env['appointment.slot'].search([
                            ('event_id', '=', self.id),
                            ('staff_id', '=', staff.id),
                            ('start_datetime', '=', start_utc),
                        ], limit=1)
                        if not existing:
                            new_slots.append({
                                'name': f"{self.name} - {staff.name}",
                                'appointment_type_id': self.appointment_type_id.id,
                                'event_id': self.id,
                                'staff_id': staff.id,
                                'start_datetime': start_utc,
                                'end_datetime': end_utc,
                            })
                        slot_start += timedelta(minutes=slot_interval_minutes)
                current_day += timedelta(days=1)
        if new_slots:
            self.env['appointment.slot'].create(new_slots)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Successfully generated %d appointment slot(s).', len(new_slots)),
                'sticky': False,
                'type': 'success',
            }
        }

    def action_view_appointments(self):
        self.ensure_one()
        appointment_ids = self.appointment_slot_ids.mapped('appointment_ids').ids
        return {
            'type': 'ir.actions.act_window',
            'name': _('Appointments'),
            'res_model': 'appointment.appointment',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', appointment_ids)],
            'context': {'create': False},
        }
