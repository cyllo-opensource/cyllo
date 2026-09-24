# -*- coding: utf-8 -*-
#############################################################################
#
#    Cyllo Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cyllo(<https://www.cyllo.com>)
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
from odoo import models, fields, api


class RepairTimeAllocationPolicy(models.Model):
    _name = 'repair.time.allocation.policy'
    _description = 'Repair Time Allocation Policy'
    _order = 'sequence, id'

    name = fields.Char(string='Name', required=True)
    sequence = fields.Integer(string='Sequence', default=10,
                              help='Policies are evaluated in order of their sequence. '
                                   'The first matching policy is applied.')
    active = fields.Boolean(default=True)
    target_type = fields.Selection([
        ('category', 'Product Category'),
        ('product', 'Specific Product')
    ], string='Target Type', default='product', required=True)
    product_category_id = fields.Many2one(
        comodel_name='product.category',
        string='Product Category',
        help='If specified, this policy will apply to products in this category.'
    )
    product_id = fields.Many2one(
        comodel_name='product.product',
        string='Product',
        help='If specified, this policy will only apply to this specific product.'
    )
    allocated_duration = fields.Float(
        string='Allocated Duration (Hours)',
        required=True,
        help='The expected time to complete the repair in hours.'
    )

    @api.onchange('target_type')
    def _onchange_target_type(self):
        """Reset related fields when switching target type"""
        if self.target_type == 'category':
            self.product_id = False
        elif self.target_type == 'product':
            self.product_category_id = False
