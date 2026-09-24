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


class ProductProduct(models.Model):
    """Inherits for adding the data of the approval records  and the
    product state's status."""
    _inherit = 'product.product'

    approver_product_line_ids = fields.One2many(
        related='product_tmpl_id.product_approver_line_ids',
        string='Approvers', help='Product approvers')
    page_approver_visibility = fields.Boolean(string='Approver Page Visibility',
                                              help='Approver page visibility')
    button_approval_visibility = fields.Boolean(readonly=False,
                                                compute='_compute_button_approval_visibility',
                                                string='Approval Visibility',
                                                help='Checking approval button visibility')
    approval_status = fields.Boolean(readonly=False,
                                     compute='_compute_approval_status',
                                     help='Check approval status')

    def _compute_button_approval_visibility(self):
        """If the approval button is visible or not to the Approval Manager"""
        for product in self:
            product.button_approval_visibility = False
            if product.env.user.id in product.approver_product_line_ids.product_approver_id.ids and \
                    product.state == 'to_approve':
                product.button_approval_visibility = True
            if product.active:
                product.button_approval_visibility = False

    def _compute_approval_status(self):
        """After approval of each manager the button to approve hides"""
        for rec in self:
            rec.approval_status = any(
                rec.product_approver_id.id == self.env.user.id and rec.status == 'approved'
                for rec in rec.approver_product_line_ids)

    @api.model_create_multi
    def create(self, vals_list):
        """
           Super Create product records and perform additional actions based
           on company settings.
           :param vals_list: List of dictionaries containing field values for
           each product being created.
           """
        res = super().create(vals_list)
        res_company = self.env.company
        if res_company.product_approver_ids:
            if (
                    res_company.minimum_cost_limit and res_company.cost_limit < res.standard_price
                    or res_company.minimum_price_limit and res_company.price_limit < res.lst_price):
                res.write({
                    'active': False,
                    'state': 'to_approve',
                    'page_approver_visibility': True
                })
        return res

    def write(self, vals):
        """
            Update the product record with the provided values and manage state
             and visibility based on company settings.
            :param vals: Dictionary of field-value pairs to be updated.
        """
        res_company = self.env.company
        if 'state' not in vals and 'active' not in vals and 'page_approver_visibility' not in vals:
            res = super().write(vals)
            if res_company.product_approver_ids:
                if (
                        res_company.product_category and self.categ_id.id in res_company.category_ids.child_id.ids +
                        res_company.category_ids.ids or res_company.minimum_cost_limit and
                        res_company.cost_limit < self.standard_price or res_company.minimum_price_limit and
                        res_company.price_limit < self.lst_price):
                    self.write({
                        'state': 'to_approve',
                        'active': False,
                        'page_approver_visibility': True
                    })

                    self._reset_approvals()
                    if self.active:
                        self.button_approval_visibility = True
                elif (
                        not res_company.minimum_cost_limit and not res_company.product_category and
                        not res_company.minimum_price_limit):
                    self.write({
                        'state': 'to_approve',
                        'active': False,
                        'page_approver_visibility': True,
                        'button_approval_visibility': True
                    })
                elif not self.active:
                    self.write({
                        'active': True,
                        'page_approver_visibility': False
                    })
            return res
        else:
            return super().write(vals)

    def action_button_approve(self):
        """Button for the product approval it will check the current user
         vote for the approval"""
        company = self.env['res.company'].browse(self.env.company.id)
        approvers = self.env['res.company'].browse(
            self.env.company.id).product_approver_ids
        if approvers:
            user = self.env.user
            line = self.approver_product_line_ids.filtered(
                lambda x: x.product_approver_id.id == user.id)
            if line and line.status == 'pending':
                line.update({'status': 'approved'})
                message = user.name + " Approved the " + self.name
                self.message_post(body=message)
                status = self.approver_product_line_ids.mapped('status')
                if company.product_approval_type == 'multi_level':
                    if 'pending' not in status and 'rejected' not in status:
                        self.write({'active': True, 'state': 'approved'})
                else:
                    self.write({'active': True, 'state': 'approved'})

    def action_product_variant_reject(self):
        """Button for the product Rejection opening wizard"""
        return {
            'name': 'Reject',
            'type': 'ir.actions.act_window',
            'res_model': 'product.reject',
            'view_mode': 'form',
            'context': {'default_button_visible': True},
            'view_id': self.env.ref(
                'cyllo_product.view_product_reject_form').id,
            'target': 'new',
        }

    def _reset_approvals(self):
        """Reset all approver lines back to pending for a new approval cycle"""
        for rec in self:
            rec.product_approver_line_ids.write({
                'status': 'pending',
            })
