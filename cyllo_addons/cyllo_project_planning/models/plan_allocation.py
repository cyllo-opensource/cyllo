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
from odoo import api, fields, models


class PlanAllocation(models.Model):
    """This model extends the 'plan.allocation' model to add additional fields."""

    _inherit = 'plan.allocation'

    project_id = fields.Many2one(
        'project.project',
        string="Project",
        compute='_compute_project_id',
        store=True,
        readonly=False
    )
    task_id = fields.Many2one(
        'project.task',
        string="Task"
    )

    @api.depends('task_id')
    def _compute_project_id(self):
        for record in self:
            if record.task_id:
                record.project_id = record.task_id.project_id
            else:
                record.project_id = record.project_id or False

    @api.onchange('project_id')
    def _onchange_project_id(self):
        if self.project_id and self.task_id and self.task_id.project_id != self.project_id:
            self.task_id = False
