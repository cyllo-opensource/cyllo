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


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    # Linked appointment types
    appointment_type_ids = fields.Many2many(
        'appointment.type', 'appointment_type_staff_rel',
        'staff_id', 'type_id',
        string='Appointment Types'
    )
    # Notification preferences
    notify_on_new_appointment = fields.Boolean(
        string='Notify on New Appointment', default=True
    )
    notify_on_cancellation = fields.Boolean(
        string='Notify on Cancellation', default=True
    )
    notify_on_reschedule = fields.Boolean(
        string='Notify on Reschedule', default=True
    )
    # Stats
    appointment_count = fields.Integer(
        string='Total Appointments', compute='_compute_appointment_count'
    )
    upcoming_appointment_count = fields.Integer(
        string='Upcoming Appointments', compute='_compute_appointment_count'
    )

    def _compute_appointment_count(self):
        today = fields.Datetime.now()
        Appointment = self.env['appointment.appointment'].sudo()
        for rec in self:
            appointments = Appointment.search([
                ('staff_id', '=', rec.id)
            ])
            rec.appointment_count = len(appointments)
            rec.upcoming_appointment_count = len(appointments.filtered(
                lambda a: a.start_datetime >= today and a.state not in (
                    'cancelled', 'rejected')
            ))

    def action_view_appointments(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Appointments - %s') % self.name,
            'res_model': 'appointment.appointment',
            'view_mode': 'list,form,calendar',
            'domain': [('staff_id', '=', self.id)],
            'context': {'default_staff_id': self.id},
        }

class HrEmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    notify_on_new_appointment = fields.Boolean(readonly=True)
    notify_on_cancellation = fields.Boolean(readonly=True)
    notify_on_reschedule = fields.Boolean(readonly=True)
