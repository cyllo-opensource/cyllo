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


class PlanAllocation(models.Model):
    """This model extends the 'project.task' model to add planned allocation functionality."""
    _inherit = 'project.task'

    plan_allocation_ids = fields.One2many(
        'plan.allocation',
        'task_id',
        string="Planned Allocation"
    )
    is_allocated = fields.Boolean(default=False)
    allocation_count = fields.Integer(compute='_compute_allocation_count')

    @api.depends('plan_allocation_ids')
    def _compute_allocation_count(self):
        """Compute the number of allocations associated with this task."""
        self.allocation_count = len(self.plan_allocation_ids)

    def action_view_allocations(self):
        """Return an action to display related allocations."""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Allocation',
            'view_mode': 'tree',
            'res_model': 'plan.allocation',
            'domain': [('task_id', '=', self.id)],
            'context': {'create': False}
        }

    def action_plan_task_allocations(self):
        """Function to creating plan allocations for tasks"""
        employee_ids = self.env['hr.employee'].search(
            [('user_id', 'in', self.user_ids.ids)]).ids
        return {
            'type': 'ir.actions.act_window',
            'name': _('Project Plan Allocation'),
            'res_model': 'project.plan.allocation',
            'target': 'new',
            'view_mode': 'form',
            'views': [[False, 'form']],
            'context': {
                'default_start_datetime': self.date_assign,
                'default_end_datetime': self.date_deadline,
                'default_employee_ids': employee_ids,
                'default_project_id': self.project_id.id,
                'default_task_id': self.id,
            }
        }
