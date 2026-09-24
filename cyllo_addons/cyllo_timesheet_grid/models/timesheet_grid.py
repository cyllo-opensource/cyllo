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
from datetime import datetime

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class TimesheetGrid(models.Model):
    """
        This model represents the backend functionality for managing timesheet
         data and related operations.
    """
    _name = "timesheet.grid"
    _description = "Timesheet Grid"

    @api.model
    def fetch_remaining_hours(self,filtered_ids):
        """
            Fetches information about remaining hours, allocated hours, and
             effective hours for the given task IDs.
            :param filtered_ids: A list of task IDs to filter the results.
            :type filtered_ids: list
            :return: A list of tuples containing the retrieved data.
            :rtype: list of tuples
        """
        if filtered_ids:
            query = '''SELECT
                    id as "id",
                    remaining_hours as "remaining_hours",
                    allocated_hours as "allocated_hours",
                    effective_hours as "effective_hours"
                    FROM
                    project_task'''
            params = (tuple(filtered_ids),)

            self.env.cr.execute(query, params)
            data = self.env.cr.fetchall()
            return data
        return []

    @api.model
    def change_hours_backend(self, project_id, task_id, float_value, js_date,
                             employee_id):
        """
            Change the unit amount of a timesheet record associated with a
            task and employee for a specific date.
            :param task_id: ID of the task.
            :param project_id: ID of the project.
            :param float_value: New unit amount value.
            :param js_date: JavaScript formatted date string
            ("%d/%m/%Y, %H:%M:%S").
            :param employee_id: ID of the employee.
            :return: True if the operation is successful.
        """
        try:
            date_obj = datetime.strptime(js_date, "%d/%m/%Y, %H:%M:%S")
        except ValueError:
            try:
                date_obj = datetime.strptime(js_date, "%d/%m/%Y, %I:%M:%S %p")
            except ValueError as e:
                raise ValidationError(_(f"Error parsing date: {e}"))
        formatted_date = date_obj.date()
        if task_id:
            task_current = self.env['project.task'].browse(task_id)
        else:
            task_current = self.env['project.project'].browse(project_id)
        data = (task_current.timesheet_ids.filtered(
            lambda rec: rec.date == formatted_date and
                        rec.employee_id.id == employee_id))
        if len(data) == 0:
            task_current.update({
                'timesheet_ids': [fields.Command.create({
                    'date': formatted_date,
                    'name': '/',
                    'unit_amount': float_value,
                    'employee_id': employee_id
                })]
            })
        elif len(data) == 1:
            data.update({
                'unit_amount': float_value
            })
        else:
            total_time = sum(data.mapped('unit_amount'))
            if float_value != total_time:
                task_current.update({
                    'timesheet_ids': [fields.Command.create({
                        'date': formatted_date,
                        'name': 'Altered Timesheet',
                        'unit_amount': float_value - total_time,
                        'employee_id': employee_id
                    })]
                })
        return True

    @api.model
    def hours_value_backend(self, project_id, task_id, employee_id, date):
        """
            Calculate and return the total unit amount of timesheet records
            associated with a task and employee for a specific date.
            :param task_id: ID of the task.
            :param project_id: ID of the project.
            :param employee_id: ID of the employee.
            :param date: JavaScript formatted date string
            ("%d/%m/%Y, %H:%M:%S").
            :return: Total unit amount for the given task, employee, and date.
        """
        try:
            date_obj = datetime.strptime(date, "%d/%m/%Y, %H:%M:%S")
        except ValueError:
            try:
                date_obj = datetime.strptime(date, "%d/%m/%Y, %I:%M:%S %p")
            except ValueError as e:
                raise ValidationError(_(f"Error parsing date: {e}"))
        formatted_date = date_obj.date()
        if task_id:
            task_current = self.env['project.task'].browse(task_id)
        else:
            task_current = self.env['project.project'].browse(project_id)
        task_data = (
            task_current.timesheet_ids.
            filtered(lambda rec: rec.date == formatted_date and rec.
                     employee_id.id == employee_id))
        return sum(task_data.mapped('unit_amount'))

    @api.model
    def overtime_work(self, args):
        """
            Calculate and return the daily work hours of an employee based
            on their user ID.
            :param args: User ID of the employee.
            :return: Daily work hours of the employee.
        """
        employee = self.env['hr.employee'].search([('user_id', '=', args)])
        return employee.resource_calendar_id.hours_per_day

    @api.model
    def timesheet_duration(self):
        """
            Retrieve timesheet duration settings from configuration parameters.
            :return: Dictionary containing minimum_duration and round_up
            settings.
        """
        settings = self.env['ir.config_parameter']
        return {'minimum_duration': settings.sudo().get_param(
            'cyllo_timesheet_grid.minimal_duration'),
                'round_up': settings.sudo().get_param(
                    'cyllo_timesheet_grid.round_up')}

    @api.model
    def day_hour_check(self):
        """
            Check the current configuration for whether time is encoded in
            days or hours.
            :return: Boolean indicating whether time is encoded in days.
        """
        is_day = self.env['res.config.settings'].sudo().search([], limit=1,
                                                               order='id desc')
        return is_day.is_encode_uom_days
