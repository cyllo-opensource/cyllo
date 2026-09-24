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
from odoo import api, Command, fields, models


class ProjectPlanAllocation(models.TransientModel):
    """This model represents a transient model for creating plan allocations
    for tasks."""
    _name = 'project.plan.allocation'
    _description = 'Project Plan Allocation'

    start_datetime = fields.Datetime(
        string="From",
        required=True
    )
    end_datetime = fields.Datetime(
        string="To",
        required=True
    )
    employee_ids = fields.Many2many(
        'hr.employee',
        string="Employees",
        required=True
    )
    allocation_type_id = fields.Many2one(
        'allocation.type',
        required=True
    )
    description = fields.Text(help="Plan allocation description")
    project_id = fields.Many2one(
        'project.project',
        related="task_id.project_id"
    )
    task_id = fields.Many2one(
        'project.task',
        readonly=True
    )
    is_modifying = fields.Boolean(default=False)

    @api.onchange('employee_ids')
    def _onchange_employee_ids(self):
        """Function to show a warning if the user modifying assignees"""
        employees = self.env['hr.employee'].search(
            [('user_id', 'in', self.task_id.user_ids.ids)])
        self.is_modifying = employees.ids != self.employee_ids.ids

    def action_plan_task_allocations(self):
        """Function for creating plan allocations for tasks"""
        plans = [self.env['plan.allocation'].create({
            'start_datetime': self.start_datetime,
            'end_datetime': self.end_datetime,
            'employee_id': employee.id,
            'allocation_type_id': self.allocation_type_id.id,
            'project_id': self.project_id.id,
            'task_id': self.task_id.id,
        }) for employee in self.employee_ids]
        self.task_id.is_allocated = True
        self.task_id.write(
            {'plan_allocation_ids': [Command.link(plan.id) for plan in plans]})
