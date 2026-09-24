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
from odoo.exceptions import ValidationError
from datetime import timedelta
import pytz


class AppointmentSlot(models.Model):
    _name = 'appointment.slot'
    _description = 'Appointment Slot'
    _order = 'start_datetime'

    name = fields.Char(string='Slot Name', required=True)
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company
    )
    appointment_type_id = fields.Many2one(
        'appointment.type', string='Appointment Type', required=True,
        ondelete='cascade'
    )
    event_id = fields.Many2one('event.event', string='Event',
                               ondelete='cascade')
    staff_domain = fields.Char(compute='_compute_staff_resource_domain')
    resource_domain = fields.Char(compute='_compute_staff_resource_domain')
    staff_id = fields.Many2one('hr.employee', string='Staff Member')
    resource_id = fields.Many2one('appointment.resource', string='Resource')
    start_datetime = fields.Datetime(string='Start', required=True)
    end_datetime = fields.Datetime(string='End', required=True,
                                   compute='_compute_end_datetime', store=True,
                                   readonly=False)
    duration = fields.Float(string='Duration (hours)',
                            related='appointment_type_id.duration')
    max_attendees = fields.Integer(
        string='Max Attendees', related='appointment_type_id.max_attendees',
        store=True
    )
    booked_count = fields.Integer(
        string='Booked', compute='_compute_booked_count'
    )
    available_count = fields.Integer(
        string='Available Spots', compute='_compute_booked_count'
    )
    is_available = fields.Boolean(
        string='Available', compute='_compute_booked_count', store=False
    )
    state = fields.Selection([
        ('available', 'Available'),
        ('partially_booked', 'Partially Booked'),
        ('fully_booked', 'Fully Booked'),
        ('blocked', 'Blocked'),
    ], string='Status', compute='_compute_booked_count', store=True)
    appointment_ids = fields.One2many(
        'appointment.appointment', 'slot_id', string='Appointments'
    )

    @api.depends('company_id', 'appointment_type_id', 'appointment_type_id.staff_ids',
                 'appointment_type_id.resource_ids')
    def _compute_staff_resource_domain(self):
        for rec in self:
            company_id = rec.company_id.id or rec.env.company.id
            if rec.appointment_type_id and rec.appointment_type_id.staff_ids:
                rec.staff_domain = f"[('appointment_type_ids', 'in', {rec.appointment_type_id.id}), ('company_id', '=', {company_id})]"
            else:
                rec.staff_domain = f"[('company_id', '=', {company_id})]"

            if rec.appointment_type_id and rec.appointment_type_id.resource_ids:
                rec.resource_domain = f"[('appointment_type_ids', 'in', {rec.appointment_type_id.id}), ('company_id', '=', {company_id})]"
            else:
                rec.resource_domain = f"[('company_id', '=', {company_id})]"

    @api.depends('start_datetime', 'duration')
    def _compute_end_datetime(self):
        for rec in self:
            if rec.start_datetime and rec.duration:
                rec.end_datetime = rec.start_datetime + timedelta(
                    hours=rec.duration)
            else:
                rec.end_datetime = rec.start_datetime

    @api.depends('appointment_ids', 'appointment_ids.state',
                 'appointment_ids.attendee_count', 'max_attendees')
    def _compute_booked_count(self):
        for rec in self:
            active_appointments = rec.appointment_ids.filtered(
                lambda a: a.state not in ('draft', 'cancelled', 'rejected')
            )
            rec.booked_count = sum(active_appointments.mapped('attendee_count'))
            rec.available_count = max(0, rec.max_attendees - rec.booked_count)
            rec.is_available = rec.available_count > 0
            if rec.booked_count == 0:
                rec.state = 'available'
            elif rec.booked_count >= rec.max_attendees:
                rec.state = 'fully_booked'
            else:
                rec.state = 'partially_booked'

    @api.constrains('start_datetime', 'end_datetime')
    def _check_dates(self):
        for rec in self:
            if rec.start_datetime and rec.end_datetime:
                if rec.end_datetime <= rec.start_datetime:
                    raise ValidationError(
                        _('End time must be after start time.'))

    @api.constrains('appointment_type_id', 'staff_id', 'resource_id')
    def _check_required_assignments(self):
        for rec in self:
            if rec.appointment_type_id.require_staff and not rec.staff_id:
                raise ValidationError(
                    _('A staff member must be assigned for this slot because its appointment type requires one.'))
            if rec.appointment_type_id.require_resource and not rec.resource_id:
                raise ValidationError(
                    _('A resource must be assigned for this slot because its appointment type requires one.'))

    @api.constrains('start_datetime', 'end_datetime', 'staff_id', 'resource_id',
                    'appointment_type_id')
    def _check_working_hours(self):
        for rec in self:
            if not rec.start_datetime or not rec.end_datetime:
                continue
            if rec.event_id:
                # Bypass working hours check for event-generated slots
                continue
            calendar = False
            if rec.staff_id and rec.staff_id.resource_calendar_id:
                calendar = rec.staff_id.resource_calendar_id
            elif rec.resource_id and rec.resource_id.working_hours_id:
                calendar = rec.resource_id.working_hours_id
            elif rec.appointment_type_id.working_hours_id:
                calendar = rec.appointment_type_id.working_hours_id
            if not calendar:
                continue
            user_tz = pytz.timezone(
                self.env.user.tz or self._context.get('tz') or 'UTC')
            start_dt = pytz.utc.localize(rec.start_datetime).astimezone(
                user_tz)
            end_dt = pytz.utc.localize(rec.end_datetime).astimezone(user_tz)
            weekday = str(start_dt.weekday())
            attendances = calendar.attendance_ids.filtered(
                lambda a: a.dayofweek == weekday)
            if not attendances:
                raise ValidationError(
                    _(
                        "You cannot create slots on days where the assigned "
                        "staff/resource has no working hours (e.g., weekends)."
                    )
                )
            start_float = start_dt.hour + start_dt.minute / 60.0
            end_float = end_dt.hour + end_dt.minute / 60.0
            if end_float == 0.0 and end_dt.date() > start_dt.date():
                end_float = 24.0
            tolerance = 0.01
            valid_time = any(
                start_float < (att.hour_to + tolerance)
                and end_float > (att.hour_from - tolerance)
                for att in attendances
            )
            if not valid_time:
                raise ValidationError(
                    _(
                        "The selected time slot falls outside the working "
                        "hours defined in the calendar."
                    )
                )

    @api.constrains(
        'appointment_type_id',
        'staff_id',
        'resource_id',
        'start_datetime',
        'end_datetime'
    )
    def _check_slot_overlap(self):
        for rec in self:
            if not rec.start_datetime or not rec.end_datetime:
                continue

            domain = [
                ('id', '!=', rec.id),
                ('appointment_type_id', '=', rec.appointment_type_id.id),
                ('start_datetime', '<', rec.end_datetime),
                ('end_datetime', '>', rec.start_datetime),
            ]
            # Check overlap for same staff
            if rec.staff_id:
                staff_overlap = self.search(
                    domain + [('staff_id', '=', rec.staff_id.id)],
                    limit=1
                )
                if staff_overlap:
                    raise ValidationError(_(
                        "Another slot already exists for this staff member "
                        "during the selected time period."
                    ))
            # Check overlap for same resource
            if rec.resource_id:
                resource_overlap = self.search(
                    domain + [('resource_id', '=', rec.resource_id.id)],
                    limit=1
                )
                if resource_overlap:
                    raise ValidationError(_(
                        "Another slot already exists for this resource "
                        "during the selected time period."
                    ))
