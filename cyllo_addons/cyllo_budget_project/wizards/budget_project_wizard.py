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
from odoo import fields, models


class BudgetProjectWizard(models.TransientModel):
    """Model used for the Wizard operation of project details in Budget"""
    _name = 'budget.project.wizard'
    _description = "Wizard for the project details in budget"

    add_create = fields.Selection(
        [('add', 'Add'), ('create', 'Create')], string="Add/Create",
        help="Choose the option to add project")
    project_id = fields.Many2one(
        'project.project', help="To add a project in budget,choose Project")
    project_name = fields.Char(help="Name for the creating Project")
    budget_id = fields.Many2one('budget.budget', help="The budget in Project")

    def action_add_project(self):
        """This defines to add budget into selected project"""
        self.project_id.budget_id = self.budget_id.id
        self.budget_id.project_id = self.project_id.id
        self.budget_id.check_project = True

    def action_create_project(self):
        """This defines to create new project with the budget """
        self.project_id = self.env['project.project'].create({
            'name': self.project_name,
            'budget_id': self.budget_id.id,
            'partner_id': False,
            'date_start': self.budget_id.start_date,
            'date': self.budget_id.end_date,
        })
        self.budget_id.project_id = self.project_id.id
        self.budget_id.check_project = True
