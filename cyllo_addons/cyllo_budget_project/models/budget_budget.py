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
from odoo import _, fields, models


class BudgetBudget(models.Model):
    """ Model used to inherit budget.budget and adding project related functions """
    _inherit = 'budget.budget'

    project_id = fields.Many2one('project.project',
                                 help='Project related to budget')
    check_project = fields.Boolean(string='Project',
                                   help='True if the budget has a project')

    def action_view_project(self):
        """This shows the Project added/created from budget when click on the
        smart button"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Project'),
            'res_model': 'project.project',
            'res_id': self.project_id.id,
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'current'
        }
