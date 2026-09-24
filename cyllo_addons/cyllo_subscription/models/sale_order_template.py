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
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class SaleOrderTemplate(models.Model):
    """Inherit the model to create a new template for subscription plan"""
    _inherit = 'sale.order.template'

    is_subscription = fields.Boolean(string='Subscription',
                                     help='If the Quotation is for subscription product enable this field')
    duration = fields.Integer(help='Duration of the subscription')
    unit = fields.Selection(selection=[('weeks', 'Weeks'), ('months', 'Months'),
                                       ('years', 'Years')],
                            help='Unit for the subscription')
    customer_can_close = fields.Boolean(string='Close By Customer',
                                        help='If customer can close this enable the field')
    order_count = fields.Integer(string='Orders',
                                 compute='_compute_order_count',
                                 help='Count of orders created')
    invoice_creation = fields.Selection(
        selection=[('manually', 'Manually'), ('draft', 'Draft'),
                   ('confirmed', 'Confirmed'), ('sent', 'Sent')],
        required=True, default='manually',
        help='Choose a invoice creation method, (Manually:- Invoices must be manually created if the manual '
             'invoice creation option is selected.; Draft:- A draft invoice is created if the draft option for '
             'invoice creation is selected; Confirmed:- If the Confirmed invoice generating mode is '
             'selected, a draft invoice is generated and automatically changes to the confirmed state when a daily '
             'scheduled action is executed. Sent:- If Sent is selected, at the time of order confirmation, '
             'a mail is sent to the consumer)')
    renewal_request = fields.Boolean(string='Customer Can Renew',
                                     help='If need to make customer to give request to renew the subscription enable '
                                          'this field')
    subscription_mail_template_id = fields.Many2one(
        'mail.template', string="Email Template",
        domain=[('model', 'in', ['account.move'])])

    def _compute_order_count(self):
        """Compute orders count"""
        for rec in self:
            rec.order_count = self.env['sale.order'].search_count(
                [('sale_order_template_id', '=', rec.id)])

    @api.onchange('sale_order_template_line_ids')
    def _onchange_sale_order_template_line_ids(self):
        """Check the product added is subscription or not"""
        subscription_products = any(
            line.product_template_id.is_subscription for line in
            self.sale_order_template_line_ids)
        non_subscription_products = any(
            not line.product_template_id.is_subscription for line in
            self.sale_order_template_line_ids)
        if subscription_products and non_subscription_products:
            raise ValidationError(
                _("Cannot add both subscription and non-subscription products."))
        if self.sale_order_template_line_ids:
            self.is_subscription = subscription_products

    def write(self, vals):
        """Super the write method to add a condition to check if the product
         added is subscription or not"""
        res = super().write(vals)
        for rec in self.sale_order_template_line_ids:
            if rec.product_template_id.is_subscription and not self.is_subscription:
                raise ValidationError(
                    _("Cannot add subscription product when Subscription is disabled"))
            elif not rec.product_template_id.is_subscription and self.is_subscription:
                raise ValidationError(
                    _("Cannot add non-subscription product when Subscription is enabled"))
        return res

    @api.model_create_multi
    def create(self, vals_list):
        """Super the write method to add a condition to check if the product
         added is subscription or not"""
        state = []
        for vals in vals_list[0]['sale_order_template_line_ids']:
            state.append(self.env['product.product'].browse(
                vals[2]['product_id']).product_tmpl_id.is_subscription)
        if False in state and vals_list[0]['is_subscription'] is True:
            raise ValidationError(
                _('Cannot add non-subscription product when Subscription is enabled'))
        elif True in state and vals_list[0]['is_subscription'] is False:
            raise ValidationError(
                _('Cannot add subscription product when Subscription is disabled'))
        return super().create(vals_list)

    def action_order(self):
        """Smart button to find the records with the plan"""
        orders = self.env['sale.order'].search(
            [('sale_order_template_id', '=', self.id)])
        return {
            'type': 'ir.actions.act_window',
            'name': _('Sale Order'),
            'res_model': 'sale.order',
            'view_mode': 'tree,form',
            'views': [(self.env.ref('cyllo_subscription.view_sale_order_tree').id,
                       'tree'),
                      (self.env.ref('cyllo_subscription.view_sale_order_form_subscription').id,
                       'form')],
            'target': 'current',
            'domain': [('id', 'in', orders.ids)],
            'context': {'default_sale_order_template_id': self.id},
        }