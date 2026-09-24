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


class ResConfigSettings(models.TransientModel):
    """Adding fields in settings of product model"""
    _inherit = 'res.config.settings'

    product_approver_ids = fields.Many2many(comodel_name='res.users',
                                            related='company_id.product_approver_ids',
                                            string='Product Approval Managers',
                                            readonly=False,
                                            domain=lambda self: [
                                                ("groups_id", "=", self.env.ref(
                                                    "cyllo_product.group_cyllo_product").id)],
                                            help='List of approvers')
    product_approval_type = fields.Selection(
        related="company_id.product_approval_type", readonly=False,
        help='Type of approval process required for products '
             'configured in this company.')
    price_limit = fields.Float(related="company_id.price_limit",
                               currency_field="currency_id", readonly=False,
                               help='Set the price Limit for the product')
    category_ids = fields.Many2many('product.category', relation='category_rel',
                                    related='company_id.category_ids',
                                    readonly=False,
                                    help='Set which category product need the approval')
    cost_limit = fields.Float(related="company_id.cost_limit",
                              currency_field="currency_id", readonly=False,
                              help='Set the cost Limit for the product')
    minimum_price_limit = fields.Boolean(
        related="company_id.minimum_price_limit", readonly=False,
        string='Price limit',
        help='Condition for the price limit')
    minimum_cost_limit = fields.Boolean(related="company_id.minimum_cost_limit",
                                        readonly=False, string='Cost Limit',
                                        help='Condition for the cost limit')
    product_category = fields.Boolean(related="company_id.product_category",
                                      readonly=False,
                                      help='Condition for the category')
    currency_id = fields.Many2one("res.currency", string="Currency",
                                  default=lambda
                                      self: self.env.company.currency_id.id
                                  )
