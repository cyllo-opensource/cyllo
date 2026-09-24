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
from odoo import _, api, Command, fields, models


class ProductTemplate(models.Model):
    """Inherit the model to add some functions to get value to the dashboard"""
    _inherit = 'product.template'

    state = fields.Selection(
        selection=[('draft', 'Draft'), ('to_approve', 'To Approve'),
                   ('approved', 'Approved'), ('rejected', 'Rejected')],
        help='State of the product', default='draft')
    product_approver_line_ids = fields.One2many('product.approve',
                                                'related_product_id',
                                                string='Product Approvers',
                                                help='Approvers assigned to this product for approval.')
    approval_button_visibility = fields.Boolean(
        compute='_compute_approval_button_visibility',
        string='Approval Visibility', help='Approval button visibility')
    approver_page_visibility = fields.Boolean(help='Approver page visibility')
    status_approval = fields.Boolean(compute='_compute_status_approval',
                                     string='Approval Status')
    type_approval = fields.Selection(
        selection=[('to_write', 'Write'), ('to_create', 'Create'),
                   ('to_unarchive', 'Un Archive'),
                   ('to_archive', 'Archive'), ('to_delete', 'Delete')],
        default='to_write')

    def _compute_approval_button_visibility(self):
        """Checking the visibility of the button approve"""
        for product in self:
            product.approval_button_visibility = False
            if product.env.user.id in product.product_approver_line_ids.product_approver_id.ids and \
                    product.state == 'to_approve':
                product.approval_button_visibility = True

    def _compute_status_approval(self):
        """After approval of each manager the button to approve hides"""
        for rec in self:
            rec.status_approval = any(
                rec.product_approver_id.id == self.env.user.id and rec.status == 'approved'
                for rec in rec.product_approver_line_ids)

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
        if not res.product_approver_line_ids:
            for approvers in res_company.product_approver_ids:
                res.write({'product_approver_line_ids': [
                    Command.create({
                        'product_approver_id': approvers.id,
                        'status': 'pending'
                    })]})
        if res_company.product_approver_ids:
            if (
                    res_company.minimum_cost_limit and res_company.cost_limit < res.standard_price
                    or res_company.minimum_price_limit and res_company.price_limit < res.list_price):
                self.write({
                    'state': 'to_approve',
                    'type_approval': 'to_create',
                    'approver_page_visibility': True
                })
                res.write({'active': False})
        return res

    def write(self, vals):
        """
            Update the product record with the provided values and manage state
             and visibility based on company settings.
            :param vals: Dictionary of field-value pairs to be updated.
        """
        if 'state' not in vals and 'active' not in vals and 'approver_page_visibility' not in vals:
            res = super().write(vals)
            res_company = self.env.company
            if res_company.product_approver_ids:
                if not self.product_approver_line_ids:
                    for approvers in res_company.product_approver_ids:
                        line_ids = self.product_approver_line_ids
                        if approvers.id in line_ids.mapped(
                                'product_approver_id.id'):
                            line_ids.filtered(lambda
                                                  rec: rec.product_approver_id.id == approvers.id).update(
                                {'status': 'pending'})
                        else:
                            self.write({'product_approver_line_ids': [
                                Command.create({
                                    'product_approver_id': approvers.id,
                                    'status': 'pending'
                                })]})

                if self.check_approval_enabled():
                    self._reset_approvals()
                    self.state = 'to_approve'
                    if self.type_approval in ['to_write', 'to_create']:
                        self.active = False
                    self.approver_page_visibility = True
                elif not self.active or self.state == 'to_approve':
                    self.write({
                        'active': True,
                        "state": "draft",
                        'approval_button_visibility': False,
                        'approver_page_visibility': False
                    })
            return res
        else:
            if self.state == 'rejected':
                vals['type_approval'] = 'to_write'
            return super().write(vals)

    def unlink(self):
        """Adding approval for the action unlink"""
        for rec in self:
            if rec.state == 'approved':
                super().unlink()
                return {
                    'type': 'ir.actions.client',
                    'tag': 'reload',
                }
            if rec.check_approval_enabled():
                rec.type_approval = 'to_delete'
                res_company = rec.env.company
                for approvers in res_company.product_approver_ids:
                    line_ids = rec.product_approver_line_ids
                    if approvers.id in line_ids.mapped(
                            'product_approver_id.id'):
                        line_ids.filtered(lambda
                                              rec: rec.product_approver_id.id == approvers.id).update(
                            {'status': 'pending'})
                    else:
                        rec.write({'product_approver_line_ids': [
                            Command.create({
                                'product_approver_id': approvers.id,
                                'status': 'pending'
                            })]})
                rec.write(
                    {'state': 'to_approve', 'approver_page_visibility': True})
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'type': 'warning',
                        'title': _('Delete Record'),
                        'message': _(
                            "Need approval for delete the product. Please refresh the page to see the approvers."),
                    }
                }
            else:
                super().unlink()
                return {
                    'type': 'ir.actions.act_window_close'
                }

    def action_unarchive(self):
        """Adding approval for the action unarchive"""
        for rec in self:
            if rec.state == 'approved':
                rec.state = 'draft'
                return super().action_unarchive()
            if rec.check_approval_enabled():
                rec.type_approval = 'to_unarchive'
                res_company = rec.env.company
                line_ids = rec.product_approver_line_ids
                for approvers in res_company.product_approver_ids:
                    if approvers.id in line_ids.mapped(
                            'product_approver_id.id'):
                        line_ids.filtered(lambda
                                              rec: rec.product_approver_id.id == approvers.id).update(
                            {'status': 'pending', 'reason': False})
                    else:
                        rec.write({'product_approver_line_ids': [
                            Command.create({
                                'product_approver_id': approvers.id,
                                'status': 'pending'
                            })]})
                    rec.write({'state': 'to_approve',
                               'approver_page_visibility': True})
            else:
                return super().action_unarchive()

    def action_archive(self):
        """Adding approval for the action archive"""
        for rec in self:
            if rec.state == 'approved':
                rec.state = 'draft'
                return super().action_archive()
            if rec.check_approval_enabled():
                rec.type_approval = 'to_archive'
                res_company = rec.env.company
                line_ids = rec.product_approver_line_ids
                for approvers in res_company.product_approver_ids:
                    if approvers.id in line_ids.mapped(
                            'product_approver_id.id'):
                        line_ids.filtered(lambda
                                              rec: rec.product_approver_id.id == approvers.id).update(
                            {'status': 'pending', 'reason': False})
                    else:
                        rec.write({'product_approver_line_ids': [
                            Command.create({
                                'product_approver_id': approvers.id,
                                'status': 'pending'
                            })]})
                rec.write(
                    {'state': 'to_approve', 'approver_page_visibility': True})
            else:
                return super().action_archive()

    def action_product_reject(self):
        """Button for the product Rejection opening wizard"""
        return {
            'name': 'Reject',
            'type': 'ir.actions.act_window',
            'res_model': 'product.reject',
            'view_mode': 'form',
            'context': {'default_button_visible': False},
            'view_id': self.env.ref(
                'cyllo_product.view_product_reject_form').id,
            'target': 'new',
        }

    def action_button_approve(self):
        """Button for the product approval it will check the current user vote
        for the approval"""
        company = self.env.company
        approvers = company.product_approver_ids
        if approvers:
            user = self.env.user
            line = self.product_approver_line_ids.filtered(
                lambda x: x.product_approver_id.id == user.id)
            if line and line.status == 'pending':
                line.update({'status': 'approved'})
                message = user.name + " Approved the " + self.name
                self.message_post(body=message)
                status = self.product_approver_line_ids.mapped('status')
                if company.product_approval_type == 'multi_level':
                    if 'pending' not in status and 'rejected' not in status:
                        self.state = 'approved'
                        if self.type_approval == 'to_archive':
                            self.action_archive()
                        elif self.type_approval == 'to_delete':
                            self.unlink()
                        else:
                            self.state = 'draft'
                            self.active = True
                else:
                    self.state = 'approved'
                    if self.type_approval == 'to_archive':
                        self.action_archive()
                    elif self.type_approval == 'to_delete':
                        self.unlink()
                    else:
                        self.state = 'draft'
                        self.active = True

    def check_approval_enabled(self):
        """Checking the approval configuration in the res.conf.settings"""
        res_company = self.env.company
        if res_company.product_approver_ids:
            if ((
                    res_company.product_category and self.categ_id.id in res_company.category_ids.child_id.ids
                    + res_company.category_ids.ids)
                    or res_company.minimum_cost_limit and res_company.cost_limit < self.standard_price
                    or res_company.minimum_price_limit and res_company.price_limit < self.list_price
                    or not any([res_company.minimum_cost_limit,
                                res_company.product_category,
                                res_company.minimum_price_limit])):
                return True
            else:
                return False
        else:
            return False

    def _reset_approvals(self):
        """Reset all approver lines back to pending for a new approval cycle"""
        for rec in self:
            rec.product_approver_line_ids.write({
                'status': 'pending',
            })
