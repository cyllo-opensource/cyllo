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


class CommissionPlanFrequency(models.Model):
    """Sales people commission plans"""
    _name = 'commission.plan.frequency'
    _description = 'Commission Frequency for Crm Commission'

    name = fields.Char(string='Period', required=True, readonly=True)
    plan_id = fields.Many2one(comodel_name='commission.plan',
                              ondelete='cascade')
    date_from = fields.Date(string='From', required=True, readonly=True)
    date_to = fields.Date(string='To', required=True, readonly=True)
    amount = fields.Monetary(string='Target')
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
