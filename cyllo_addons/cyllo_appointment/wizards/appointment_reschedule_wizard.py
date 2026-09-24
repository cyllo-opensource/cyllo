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
from datetime import timedelta
import logging

_logger = logging.getLogger(__name__)


class AppointmentRescheduleWizard(models.TransientModel):
    _name = 'appointment.reschedule.wizard'
    _description = 'Reschedule Appointment Wizard'

    appointment_id = fields.Many2one(
        'appointment.appointment', string='Appointment',
        required=True, readonly=True
    )
    current_start = fields.Datetime(
        string='Current Start', related='appointment_id.start_datetime',
        readonly=True
    )
    new_start_datetime = fields.Datetime(string='New Start Date & Time',
                                         required=True)
    new_end_datetime = fields.Datetime(
        string='New End Date & Time', compute='_compute_new_end', store=True,
        readonly=False
    )
    reschedule_reason = fields.Text(string='Reason for Rescheduling')
    notify_customer = fields.Boolean(string='Notify Customer', default=True)
    notify_staff = fields.Boolean(string='Notify Staff', default=True)

    @api.depends('new_start_datetime',
                 'appointment_id.appointment_type_id.duration')
    def _compute_new_end(self):
        for rec in self:
            if rec.new_start_datetime and rec.appointment_id.appointment_type_id:
                duration = rec.appointment_id.appointment_type_id.duration
                rec.new_end_datetime = rec.new_start_datetime + timedelta(
                    hours=duration)
            else:
                rec.new_end_datetime = rec.new_start_datetime

    @api.constrains('new_start_datetime')
    def _check_new_start(self):
        for rec in self:
            appt = rec.appointment_id
            if appt and appt.appointment_type_id:
                min_notice = appt.appointment_type_id.min_booking_notice
                if min_notice > 0:
                    min_start = fields.Datetime.now() + timedelta(
                        hours=min_notice)
                    if rec.new_start_datetime < min_start:
                        raise UserError(_(
                            'This appointment type requires at least %s hour(s) advance notice.'
                        ) % min_notice)

    def action_confirm_reschedule(self):
        self.ensure_one()
        appt = self.appointment_id
        appt.write({
            'original_start_datetime': appt.start_datetime if not appt.original_start_datetime else appt.original_start_datetime,
            'start_datetime': self.new_start_datetime,
            'end_datetime': self.new_end_datetime,
            'is_rescheduled': True,
            'reschedule_count': appt.reschedule_count + 1,
            'reschedule_reason': self.reschedule_reason,
        })
        msg = _('Appointment rescheduled from %s to %s.') % (
            self.current_start, self.new_start_datetime
        )
        if self.reschedule_reason:
            msg += _(' Reason: %s') % self.reschedule_reason
        appt._message_log(body=msg)
        # Send Customer Reschedule Email
        if self.notify_customer:
            cust_tmpl = self.env.ref(
                'cyllo_appointment.email_template_appointment_rescheduled',
                raise_if_not_found=False)
            if cust_tmpl:
                try:
                    cust_tmpl.send_mail(appt.id, force_send=True)
                except Exception as e:
                    _logger.warning(
                        "Failed to send customer reschedule email for %s: %s",
                        appt.name, str(e))
        # Send Staff Reschedule Email
        if self.notify_staff and appt.staff_id and appt.staff_id.notify_on_reschedule and appt.staff_id.work_email:
            staff_tmpl = self.env.ref(
                'cyllo_appointment.email_template_appointment_rescheduled_staff',
                raise_if_not_found=False)
            if staff_tmpl:
                try:
                    staff_tmpl.send_mail(appt.id, force_send=True)
                except Exception as e:
                    _logger.warning(
                        "Failed to send staff reschedule email for %s: %s",
                        appt.name, str(e))

        return {'type': 'ir.actions.act_window_close'}
