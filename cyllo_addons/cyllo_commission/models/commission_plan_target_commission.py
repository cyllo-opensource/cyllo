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


class CommissionPlanTargetCommission(models.Model):
    """Target Commission plans"""
    _name = 'commission.plan.target.commission'
    _description = 'Crm Commission Based on Commission Target'

    plan_id = fields.Many2one(comodel_name='commission.plan',
                              ondelete='cascade')
    target_rate = fields.Float(string='Target Rate(%)')
    amount_rate = fields.Float(string='OTC (%)', compute='_compute_amount_rate',
                               inverse='_inverse_amount_rate', store=True)
    amount = fields.Monetary(string='Commission', compute='_compute_amount',
                             inverse='_inverse_amount', store=True)
    company_id = fields.Many2one('res.company', store=True, copy=False,
                                 string="Company",
                                 default=lambda
                                     self: self.env.user.company_id.id)
    currency_id = fields.Many2one('res.currency', string="Currency",
                                  related='company_id.currency_id',
                                  default=lambda
                                      self: self.env.user.company_id.currency_id.id)
    user_id = fields.Many2one('res.users', string='User',
                              default=lambda self: self.env.user,
                              )

    @api.depends('amount', 'plan_id.commission_amount')
    def _compute_amount_rate(self):
        """Compute the amount rate based on the commission amount and the target amount."""
        for record in self:
            if record.plan_id.commission_amount and record.amount:
                record.amount_rate = (
                        record.amount / record.plan_id.commission_amount)
            else:
                record.amount_rate = 0.0

    def _inverse_amount_rate(self):
        """Inverse method to set the amount based on the amount rate and commission amount."""
        for record in self:
            if record.plan_id.commission_amount and record.amount_rate:
                record.amount = (
                        record.plan_id.commission_amount * record.amount_rate)
            else:
                record.amount = 0.0

    @api.depends('amount_rate', 'plan_id.commission_amount')
    def _compute_amount(self):
        """Compute the amount based on the amount rate and commission amount."""
        for record in self:
            if record.plan_id.commission_amount and record.amount_rate:
                record.amount = (
                            record.plan_id.commission_amount * record.amount_rate)
            else:
                record.amount = 0.0

    def _inverse_amount(self):
        """Inverse method to set the amount rate based on the amount and commission amount."""
        for record in self:
            if record.plan_id.commission_amount and record.amount:
                record.amount_rate = (
                            record.amount / record.plan_id.commission_amount)
            else:
                record.amount_rate = 0.0
