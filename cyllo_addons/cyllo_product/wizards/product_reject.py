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
from odoo import _, fields, models


class ProductReject(models.TransientModel):
    """Transient model to create wizard for rejection of the product"""
    _name = 'product.reject'
    _description = 'Product Reject'

    rejection_reason = fields.Text(required=True,
                                   help='Give reason for rejection')
    button_visible = fields.Boolean(string='Reject button visible',
                                    default=True,
                                    help='To enable and hide the rejection button')

    def action_reject_product(self):
        """Button to reject th e product template"""
        product = self.env['product.template'].browse(
            self.env.context.get('active_id'))
        company = self.env.company
        approvers = company.product_approver_ids
        if approvers:
            line = product.product_approver_line_ids.filtered(
                lambda x: x.product_approver_id.id == self.env.user.id)
            if line and line.status == 'pending':
                line.update(
                    {'status': 'rejected', 'reason': self.rejection_reason})
                product.message_post(body=_(
                    f'product {product.name} is Rejected because: {self.rejection_reason}'),
                                     message_type='comment',
                                     subtype_xmlid='mail.mt_comment')
                status = list(
                    product.product_approver_line_ids.mapped('status'))
                if company.product_approval_type == 'multi_level':
                    if 'pending' or 'approved' not in status:
                        if product.type_approval == 'to_create':
                            product.write(
                                {'active': False, 'state': 'rejected'})
                        else:
                            product.write({'state': 'rejected'})
                else:
                    if product.type_approval == 'to_create':
                        product.write({'active': False, 'state': 'rejected'})
                    else:
                        product.write({'state': 'rejected'})

    def action_reject_product_variant(self):
        """Button to reject th e product variant"""
        product = self.env['product.product'].browse(
            self.env.context.get('active_id'))
        company = self.env['res.company'].browse(self.env.company.id)
        approvers = self.env['res.company'].browse(
            self.env.company.id).product_approver_ids
        if approvers:
            line = product.product_approver_line_ids.filtered(
                lambda x: x.product_approver_id.id == self.env.user.id)
            if line and line.status == 'pending':
                line.update(
                    {'status': 'rejected', 'reason': self.rejection_reason})
                product.message_post(body=_(
                    f'Product {product.name} is rejected because: {self.rejection_reason}'),
                                     message_type='comment',
                                     subtype_xmlid='mail.mt_comment')
                status = list(
                    product.approver_product_line_ids.mapped('status'))
                if company.product_approval_type == 'multi_level':
                    if 'pending' or 'approved' not in status:
                        product.write({'active': False, 'state': 'rejected'})
                else:
                    product.write({'active': False, 'state': 'rejected'})
