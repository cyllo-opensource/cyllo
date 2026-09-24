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
from odoo import fields, models, _


class CrmLead(models.Model):
    """Inherits the base crm.lead model and adds Tasks information in the lead form."""
    _inherit = 'crm.lead'

    task_id = fields.Many2one('project.task',string='Task')

    def action_create_task(self):
        """Create a task from this lead and get its ID"""
        project = self.env.ref('cyllo_crm_project.project_crm_leads',
                               raise_if_not_found=False)
        task_vals = {
            'name': self.name,
            'partner_id': self.partner_id.id if self.partner_id else False,
            'project_id': project.id if project else False,
        }
        task = self.env['project.task'].create(task_vals)
        self.task_id = task.id
        return {
            'type': 'ir.actions.act_window',
            'name': _('Task'),
            'res_model': 'project.task',
            'res_id': task.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_open_task(self):
        """Open task from this lead and get its ID"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Task'),
            'res_model': 'project.task',
            'res_id': self.task_id.id,
            'view_mode': 'form',
            'target': 'current',
        }