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


class CommissionContribution(models.Model):
    """Commission plan Achievements"""
    _name = 'commission.contribution'
    _description = 'Crm Commission Based on Achievements'

    plan_id = fields.Many2one(comodel_name='commission.plan',
                              ondelete='cascade')
    type_id = fields.Many2one('commission.type', string='Type',
                              required=True)
    rate = fields.Float(string='Rate (%)', required=True, default=0.02)
    order_ids = fields.Many2many('sale.order', string='Orders',
                                 compute='_compute_order_ids')
    order_line_ids = fields.Many2many('sale.order.line', string='Order Lines',
                                      compute='_compute_order_ids')

    @api.depends(
        # Plan-related dependencies
        'plan_id.state',
        # Team-related orders and pipeline stages
        'plan_id.team_id',
        'plan_id.team_id.order_ids.state',
        'plan_id.team_id.order_ids.payment_state',
        'plan_id.team_id.order_ids.order_line.price_subtotal_latest',
        'plan_id.team_id.order_ids.opportunity_id.stage_id',
        # Salesperson-related orders and pipeline stages
        'plan_id.user_ids.user_id.order_ids.state',
        'plan_id.user_ids.user_id.order_ids.payment_state',
        'plan_id.user_ids.user_id.order_ids.order_line.price_subtotal_latest',
        'plan_id.user_ids.user_id.order_ids.opportunity_id.stage_id',
        # Type config dependencies
        'type_id.type',
        'type_id.crm_rule_to_apply',
        'type_id.sales_rule_to_apply',
    )
    def _compute_order_ids(self):
        """Compute order and order line IDs based on the type of commission contribution."""
        for record in self:
            record.order_line_ids = []
            record.order_ids = []
            if record.type_id and record.type_id.type == 'sale':
                domain = eval(
                    record.type_id.sales_rule_to_apply) if record.type_id.sales_rule_to_apply else []
                domain.append(('order_id.is_paid', '=', True))
                order_lines = self.env['sale.order.line'].search(domain)
                orders = order_lines.mapped('order_id')
                record.order_line_ids = order_lines.ids
                record.order_ids = orders.ids
            elif record.type_id and record.type_id.type == 'crm':
                domain = eval(
                    record.type_id.crm_rule_to_apply) if record.type_id.crm_rule_to_apply else []
                leads = self.env['crm.lead'].search(domain)
                orders = self.env['sale.order'].search(
                    [('opportunity_id', 'in', leads.ids),
                     ('is_paid', '=', True)])
                record.order_ids = orders.ids
