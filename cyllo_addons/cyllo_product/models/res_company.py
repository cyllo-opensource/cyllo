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


class ResCompany(models.Model):
    """Adding fields for approval actions"""
    _inherit = 'res.company'

    product_approver_ids = fields.Many2many(comodel_name='res.users',
                                            string='Product Approval Managers',
                                            relation="product_approver_rel",
                                            domain=lambda self: [
                                                ("groups_id", "=", self.env.ref(
                                                    "cyllo_product.group_cyllo_product").id)],
                                            help='List of approvers')
    product_approval_type = fields.Selection(selection=[
        ('single_level', 'Single Level'), ('multi_level', 'Multi Level')])
    price_limit = fields.Float(help='Set the price Limit for the product')
    category_ids = fields.Many2many('product.category', relation="category_rel",
                                    help='Set which category product need the approval')
    cost_limit = fields.Float(string='Cost Limit Amount',
                              help='Set the cost Limit for the product')
    minimum_price_limit = fields.Boolean(string='Price limit',
                                         help='Condition for the price limit')
    minimum_cost_limit = fields.Boolean(string='Cost Limit',
                                        help='Condition for the cost limit')
    product_category = fields.Boolean(help='Condition for the category')
