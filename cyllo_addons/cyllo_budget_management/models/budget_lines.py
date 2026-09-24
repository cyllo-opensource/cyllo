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
from odoo.exceptions import ValidationError


class BudgetLines(models.Model):
    """ Model used to store budget lines, perform budget related functions """
    _name = 'budget.lines'
    _description = 'Budget Management Lines'

    display_name = fields.Char(help='display name of document request')
    account_ids = fields.Many2many('account.account', string='Accounts')
    analytic_account_id = fields.Many2one(
        'account.analytic.account', domain="[('id','in',analytic_account_ids)]",
        help='The Analytic account of the budget Line')
    include_child = fields.Boolean(help="Including child details")
    analytic_account_ids = fields.Many2many(
        'account.analytic.account', compute='_compute_analytic_account_ids',
        help='The Analytic account of the budget Line')
    start_date = fields.Date(help='The Start date of budget', required=True,
                             compute='_compute_start_date',
                             readonly=False, store=True)
    end_date = fields.Date(help='The End date of budget', required=True)
    budget_type = fields.Selection(
        string='Earn/Spend', selection=[('earn', 'Earn'), ('spend', 'Spend')],
        help="choose Earn/ Spend", required=True)
    planned_amount = fields.Monetary(
        string='Amount', help='Planned amount for the Budget Line ',
        currency_field='currency_id')
    practical_amount = fields.Monetary(
        help='The Amount You earned/spent', readonly=True,
        currency_field='currency_id')
    theoretical_amount = fields.Monetary(
        help='The Amount You Supposed to  earn/spend at this date',
        compute='_compute_theoretical_amount', currency_field='currency_id')
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.user.company_id.currency_id.id)
    achievement = fields.Float(
        help='Shows the ratio between practical amount and theoretical amount',
        readonly=True)

    budget_id = fields.Many2one(
        'budget.budget', help='Refers the budget of line')
    stage = fields.Selection(
        selection=[('success', 'Success'), ('positive', 'Positive'),
                   ('fail', 'Failed'), ('negative', 'Negative')],
        help="stages of the budget management")
    check_configuration = fields.Boolean()
    company_id = fields.Many2one(
        'res.company', 'Company', readonly=True,
        default=lambda self: self.env.user.company_id,
        help='Name of the company of the user')

    @api.depends('budget_id.start_date', 'budget_id.end_date')
    def _compute_start_date(self):
        """Compute start and end date based on the budget start date and end date"""
        for record in self:
            record.start_date = record.budget_id.start_date if record.budget_id.start_date else False
            record.end_date = record.budget_id.end_date if record.budget_id.end_date else False

    @api.depends('planned_amount', 'start_date', 'end_date')
    def _compute_theoretical_amount(self):
        """ Compute Theoretical Amount Based on Planned Amount
        The Theoretical Amount represents the amount of money you theoretically
        could have spent or should have received based on the date.
        For example, suppose your budget is 1200 for 12 months
        (January to December), and today is 31 of January. In that case, the
        theoretical amount will be 100 since this is the actual amount
        that could have been made."""
        for record in self:
            if record.start_date and record.end_date and record.start_date <= record.end_date:
                if record.start_date <= fields.date.today() <= record.end_date:
                    record.theoretical_amount = (record.planned_amount / int(
                        (record.end_date - record.start_date).days + 1)) * (int(
                        (fields.date.today() - record.start_date).days) + 1)
                elif record.end_date < fields.date.today():
                    record.theoretical_amount = record.planned_amount
                else:
                    record.theoretical_amount = 0
            else:
                record.theoretical_amount = 0

    @api.depends('budget_id')
    def _compute_analytic_account_ids(self):
        """Compute analytic accounts that has no parent """
        for record in self:
            record.analytic_account_ids = self.env[
                'account.analytic.account'].search(
                [('analytic_account_id', '=', False)])

    def action_budget_configuration(self):
        """This method manages the configuration of budget lines"""
        self.check_configuration = True
        for record in self.analytic_account_id.analytic_account_ids:
            if record not in self.env['budget.lines.configuration'].search(
                    [('budget_line_id', '=', self.id)]).mapped(
                'analytic_account_id'):
                self.env['budget.lines.configuration'].create({
                    'budget_line_id': self.id,
                    'analytic_account_id': record.id,
                })
        if self.budget_id.state in ('confirm', 'approve', 'reject'):
            context = {
                'edit': False
            }
        else:
            context = {}
        return {
            'type': 'ir.actions.act_window',
            'name': _("Budget Lines Configuration"),
            'res_model': 'budget.lines.configuration',
            'view_mode': 'tree',
            'domain': [('budget_line_id', '=', self.id)],
            'context': context,
            'views': [
                (self.env.ref(
                    'cyllo_budget_management.view_budget_lines_configuration_tree').id,
                 'list'),
            ],
        }

    def action_budget_configuration_view(self):
        """This method manages the configuration of budget lines"""
        if self.budget_id.state in ('confirm', 'approve', 'reject'):
            context = {
                'edit': False
            }
        else:
            context = {}
        return {
            'type': 'ir.actions.act_window',
            'name': _("Budget Lines Configuration"),
            'res_model': 'budget.lines.configuration',
            'view_mode': 'tree',
            'domain': [('budget_line_id', '=', self.id)],
            'context': context,
            'views': [
                (self.env.ref(
                    'cyllo_budget_management.view_budget_lines_configuration_tree').id,
                 'list'),
            ],
        }

    @api.constrains('start_date', 'end_date')
    def _check_start_date(self):
        """Checks if the start and end dates of the budget line are within the budget's start and end dates.
        If not, raises a ValidationError."""
        for record in self:
            if record.start_date:
                if (
                        record.budget_id.start_date and record.start_date < record.budget_id.start_date) or (
                        record.budget_id.end_date and record.start_date > record.budget_id.end_date):
                    raise ValidationError(
                        _('"Start Date" of the budget line should be included '
                          'in the Period of the budget'))
            if record.end_date:
                if (
                        record.budget_id.start_date and record.end_date < record.budget_id.start_date) or (
                        record.budget_id.end_date and record.end_date > record.budget_id.end_date):
                    raise ValidationError(
                        _('"End Date" of the budget line should be included in '
                          'the Period of the budget'))
            if record.start_date and record.end_date and record.start_date > record.end_date:
                raise ValidationError(_('"End Date" should be greater than '
                                        '"Start Date"'))

    @api.onchange('planned_amount')
    def _onchange_planned_amount(self):
        """ This method is triggered when the `planned_amount` field is changed.
        It first calls the `_onchange_budget_type` method to adjust the
        `planned_amount` based on the `budget_type`.
       """
        if self.planned_amount:
            self._onchange_budget_type()

    @api.onchange('budget_type')
    def _onchange_budget_type(self):
        """This method is triggered when the `budget_type` field is changed.
        If the `budget_type` is `spend` and `planned_amount` is positive,
        it changes `planned_amount` to negative.
        If the `budget_type` is `earn` and `planned_amount` is negative,
        it changes `planned_amount` to positive."""
        if self.budget_type == 'spend' and self.planned_amount > 0:
            self.planned_amount = - self.planned_amount
        elif self.budget_type == 'earn' and self.planned_amount < 0:
            self.planned_amount = - self.planned_amount

    def action_view_moves(self):
        """
           This action opens a view  for the model `account.move.line`.
           The view only includes records that have a `parent_state` of
           `posted`, an `account_id` in the list of account ids associated with
           the current budget line's category, and a `date`
           that falls within the start and end dates of the current budget line.
           """
        if self.analytic_account_id:
            if self.include_child:
                analytic_accounts = self.analytic_account_id.analytic_account_ids.ids
                analytic_accounts.append(self.analytic_account_id.id)
            else:
                analytic_accounts = [self.analytic_account_id.id]
            moves = self.env['account.analytic.line'].search(
                [('date', '>=', self.start_date),
                 ('date', '<=', self.end_date),
                 ('account_id', 'in', analytic_accounts)])
            if self.account_ids:
                moves = moves.filtered(lambda
                                           rec: rec.general_account_id.id in self.account_ids.ids)
            return {
                'type': 'ir.actions.act_window',
                'name': _('Entries'),
                'res_model': 'account.analytic.line',
                'domain': [('id', 'in', moves.ids)],
                'views': [[False, 'tree'], [False, 'form']],
            }
        else:
            accounts = self.account_ids.ids
            moves = self.env['account.move.line'].search(
                [('date', '>=', self.start_date), ('date', '<=', self.end_date),
                 ('account_id', 'in', accounts)]).ids
            return {
                'type': 'ir.actions.act_window',
                'name': _('Entries'),
                'res_model': 'account.move.line',
                'domain': [('id', 'in', moves)],
                'views': [[False, 'tree'], [False, 'form']],
            }

    @api.constrains('account_ids', 'analytic_account_id')
    def _check_account_ids(self):
        """ Check the budget accounts to ensure they meet specified criteria."""
        for record in self:
            if not record.account_ids and not record.analytic_account_id:
                raise ValidationError(
                    _('Please Select Any of the accounts, Either Chart of '
                      'account or Analytic Account'))
