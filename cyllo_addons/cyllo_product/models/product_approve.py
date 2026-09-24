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


class ProductApprove(models.Model):
    """Model is used add the product form page approve record line"""
    _name = 'product.approve'
    _description = 'Product Approval Lines'

    product_approver_id = fields.Many2one('res.users', string='Approver',
                                          help='Product approval user')
    status = fields.Selection(
        selection=[('pending', 'Pending'), ('approved', 'Approved'),
                   ('rejected', 'Rejected')],
        help="The status of each product's request for approval")
    related_product_id = fields.Many2one('product.template',
                                         string='Product approve id',
                                         help='Used to connect the product module')
    product_product_id = fields.Many2one('product.product', string='Product',
                                         help='Product variant')
    reason = fields.Char(help='Reason for the rejection')
