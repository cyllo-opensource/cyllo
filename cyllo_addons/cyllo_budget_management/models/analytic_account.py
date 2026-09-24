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


class AccountAnalyticAccount(models.Model):
    """ Model used to inherit analytic.account and adding Budget lines in Analytic """
    _inherit = 'account.analytic.account'

    analytic_account_id = fields.Many2one(
        'account.analytic.account', help='Parent of the Analytic Account',
        domain="[('id','in',parent_ids)]")
    parent_ids = fields.Many2many(
        'account.analytic.account', 'analytic_parents_rel', column1='name',
        compute='_compute_parent_ids')
    analytic_account_ids = fields.Many2many(
        'account.analytic.account', relation='child_analytic_account_rel',
        column1='analytic_account_id', help='Child of Analytic Account',
        compute='_compute_analytic_account_ids')
    budget_line_ids = fields.One2many('budget.lines', 'analytic_account_id')

    @api.depends('name')
    def _compute_parent_ids(self):
        """Compute Parent Ids"""
        for record in self:
            if not record.analytic_account_ids:
                record.parent_ids = self.search(
                    [('id', '!=', record._origin.id),
                     ('analytic_account_id', '=', False)])
            else:
                record.parent_ids = False

    @api.depends('analytic_account_id')
    def _compute_analytic_account_ids(self):
        """Compute The Analytic accounts"""
        for record in self:
            record.analytic_account_ids = self.search(
                [('analytic_account_id', '=', record.id)])

    @api.depends('budget_line_ids')
    def _compute_budget_line_ids(self):
        """Compute budget Lines"""
        for record in self:
            record.budget_line_ids = self.env['budget.lines'].search(
                [('analytic_account_id', '=', record.id)])

    @api.model
    def create(self, vals):
        """Super the create function to set plan id of Parent Account"""
        res = super(AccountAnalyticAccount, self).create(vals)
        if vals.get('analytic_account_id'):
            res.plan_id = res.analytic_account_id.plan_id.id
        return res

    def write(self, vals):
        """Super the Write function to set plan id of Parent Account"""
        if vals.get('analytic_account_id'):
            parent = self.env['account.analytic.account'].browse(
                int(vals.get('analytic_account_id')))
            vals['plan_id'] = parent.plan_id.id
        elif self.analytic_account_id:
            vals['plan_id'] = self.analytic_account_id.plan_id.id
        return super(AccountAnalyticAccount, self).write(vals)

    @api.onchange('analytic_account_id')
    def _onchange_analytic_account_id(self):
        """Change the plan Based on the Parent Selected"""
        if self.analytic_account_id:
            self.plan_id = self.analytic_account_id.plan_id.id
