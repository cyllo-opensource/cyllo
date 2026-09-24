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


class ProjectProject(models.Model):
    """ Model used to store budget details in project, perform budget related functions """
    _inherit = 'project.project'

    budget_id = fields.Many2one('budget.budget', 'Budget',
                                help='The budget related to the Project')

    def action_view_budget(self):
        """This shows the budget related to the project in when clicking on
        the smart button"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Budget'),
            'res_model': 'budget.budget',
            'res_id': self.budget_id.id,
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'current'
        }
