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

class Task(models.Model):
    _inherit = "project.task"

    reduced_emissions = fields.Float(string="Reduced Emissions (kgCO²e)")
    recycled_water = fields.Float(string="Recycled Water (KL)", help="Amount of recycled/recovered water in this task.")
    scope_id = fields.Many2one('carbon.scope', string="Scope")

    is_water_project = fields.Boolean(compute='_compute_project_type')
    is_green_project = fields.Boolean(compute='_compute_project_type')

    @api.depends('project_id', 'project_id.name')
    def _compute_project_type(self):
        for task in self:
            name = task.project_id.name or ''
            task.is_water_project = 'Water' in name
            task.is_green_project = 'Green' in name
