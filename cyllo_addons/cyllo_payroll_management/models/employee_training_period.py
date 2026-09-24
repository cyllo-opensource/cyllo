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
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
import datetime


class EmployeeTrainingPeriod(models.Model):
    """To add the employees training period before the contract"""
    _name = 'employee.training.period'
    _description = 'Employee Training Period'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'employee_id'

    employee_id = fields.Many2one('hr.employee', help='To add the employee name', required=True)
    start_date = fields.Date(help='Start date of training', required=True)
    end_date = fields.Date(help='End date of training', required=True)
    extended_end_date = fields.Date(help="Extended end date of training",compute='_compute_end_date',store=True)
    job_position_id = fields.Many2one(related="employee_id.job_id", help="Current employee job position")
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    time_off_ids = fields.Many2many('hr.leave', help='Time off allocated')
    reduce_half_day = fields.Boolean(help='To reduce a full when two half days are refused',default=False)
    state = fields.Selection([('new', 'New'), ('done','Completed'), ('extended', 'Extended')], required=True, default='new')

    @api.onchange('start_date', 'end_date')
    def _onchange_start_date(self):
        """Check if start_date is before or equal to end_date."""
        if self.start_date and self.end_date and not self.start_date < self.end_date:
            raise ValidationError(_("End date must be grater than the start date"))

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        """Check whether the employee already has a training period."""
        if self.employee_id:
            existing_training_periods = self.env['employee.training.period'].search(
                [('employee_id', '=', self.employee_id.id)])
            if existing_training_periods:
                raise ValidationError(_("This employee already has a training period."))

    @api.depends('time_off_ids', 'time_off_ids.state')
    def _compute_end_date(self):
        """Compute the date extension based on time_off_ids approved."""
        for record in self:
            end_date = 0
            half_day = []
            extended_time_offs = record.time_off_ids.filtered(
                lambda time_off:
                time_off.state == 'validate' and time_off.holiday_status_id.extend_training
            )
            for time_off in  extended_time_offs:
                if time_off.request_unit_half: half_day.append(time_off.id)
                else: end_date += time_off.number_of_days
            end_date += len(half_day)//2
            record.extended_end_date = record.end_date + datetime.timedelta(days=end_date)
            record.state = 'new' if record.extended_end_date == record.end_date else 'extended'