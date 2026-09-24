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
from datetime import timedelta

from odoo import api, fields, models


def get_date_list(from_date, to_date):
    """
        This method generates a list of dates between two given dates
        (inclusive).
        Parameters:
        from_date (date): The start date
        to_date (date): The end date
        Returns:
        list: A list of dates from `from_date` to `to_date`
        """
    date_list = []
    if from_date and to_date:
        current_date = from_date
        while current_date <= to_date:
            date_list.append(current_date)
            current_date += timedelta(days=1)
        return date_list


class BudgetLines(models.Model):
    """ Model used to inherit budget.lines and adding sales person target
     related functions """
    _inherit = 'budget.lines'

    crm_team_member_id = fields.Many2one(
        'crm.team.member', string='Sales Person',
        help="choose the sales person")
    crm_achievement = fields.Monetary(
        string='Sales Person Achievement',
        help='Get the details of salesperson achieved the target or not',
        compute='_compute_crm_achievement', currency_field='currency_id')

    @api.depends('crm_team_member_id')
    def _compute_crm_achievement(self):
        """
           Compute the achievement of a salesperson (CRM team member) based on
           the total price of account moves that fall within the common dates
           between the CRM team member's start and end dates
           and the budget line's start and end dates.
           """
        for record in self:
            if (
                    record.crm_team_member_id and record.crm_team_member_id.start_date and
                    record.crm_team_member_id.end_date and record.start_date and record.end_date):
                crm_date_list = get_date_list(
                    record.crm_team_member_id.start_date,
                    record.crm_team_member_id.end_date)
                budget_line_date_list = get_date_list(
                    record.start_date, record.end_date)
                common_dates = list(set(crm_date_list).intersection(set(
                    budget_line_date_list)))
                if record.analytic_account_id:
                    analytic_accounts = record.analytic_account_id.analytic_account_ids.ids
                    analytic_accounts.append(record.analytic_account_id.id)
                    if not record.account_ids:
                        moves = (self.env['account.analytic.line'].search(
                            [('account_id', 'in', analytic_accounts),
                             ('date', 'in', common_dates)]))
                    else:
                        moves = (self.env['account.analytic.line'].search(
                            [('account_id', 'in', analytic_accounts),
                             ('general_account_id', 'in',
                              record.account_ids.ids),
                             ('date', 'in', common_dates)]))
                    record.crm_achievement = sum(moves.filtered(
                        lambda
                            rec: rec.move_line_id.move_id.invoice_user_id.id == record.crm_team_member_id.user_id.id).mapped(
                        'amount'))
                else:
                    moves = self.env['account.move.line'].search(
                        [('date', 'in', common_dates),
                         ('account_id', 'in', record.account_ids.ids)])
                    record.crm_achievement = -sum(moves.filtered(
                        lambda
                            rec: rec.move_id.invoice_user_id.id == record.crm_team_member_id.user_id.id).mapped(
                        'balance'))
            else:
                record.crm_achievement = 0
