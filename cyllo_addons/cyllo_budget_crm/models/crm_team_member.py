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


class CrmTeamMember(models.Model):
    """ Model used to inherit crm.team.member and adding target related
     calculation """
    _inherit = 'crm.team.member'

    target_amount = fields.Monetary(string="Target", help='Target Amount',
                                    currency_field='currency_id')
    start_date = fields.Date(
        help='Choose the start date. Note that only the budget lines with start'
             ' dates greater than this start date will be selected here.')
    end_date = fields.Date(
        help='Choose the start date. Note that only the budget lines with end'
             ' dates less than this end date will be selected here.')
    budget_line_ids = fields.Many2many(
        'budget.lines', string="Budget Lines",
        compute='_compute_budget_line_ids')
    state = fields.Selection(
        selection=[('achieved', 'Achieved'), ('not_achieved', 'Not Achieved')],
        compute='_compute_state', help="Target Achieved or Not")
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.user.company_id.currency_id.id)
    compute_group = fields.Boolean(compute='_compute_groups_read')

    @api.depends('start_date', 'end_date', 'target_amount')
    def _compute_budget_line_ids(self):
        """
           Compute the budget lines associated with each record.
           This method searches for budget lines that are associated with the
           current CRM team member record and fall within the start and end
           dates of the record.
           """
        for record in self:
            record.budget_line_ids = self.env['budget.lines'].search([
                ('crm_team_member_id', '=', record.id),
                ('start_date', '>=', record.start_date),
                ('end_date', '<=', record.end_date)
            ])

    @api.depends('budget_line_ids')
    def _compute_state(self):
        """
           Compute the state of the CRM team member based on the total
           achievement from the budget lines.
           If the total achievement is greater than or equal to the target
           amount, the state is set to `achieved`.
           Otherwise, the state is set to `not_achieved`.
           """
        for record in self:
            total = 0
            for line in record.budget_line_ids:
                total += line.crm_achievement
            if total >= record.target_amount:
                record.state = 'achieved'
            else:
                record.state = 'not_achieved'

    @api.depends('start_date', 'end_date', 'target_amount')
    def _compute_groups_read(self):
        """Check Only Administrator Can Edit The Field"""
        for record in self:
            if self.user_has_groups('sales_team.group_sale_manager'):
                record.compute_group = True
            else:
                record.compute_group = False
