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
from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class SaleOrder(models.Model):
    """Inherit the model and creating a model for subscription"""
    _inherit = "sale.order"

    is_subscription = fields.Boolean(
        help='If the product added is a subscription product then this field is true',
        compute='_compute_is_subscription', store=True)
    state_subscription = fields.Selection(
        selection=[('quotation', 'Subscription Quotation'),
                   ('sub_order', 'Subscription Order Created')],
        default='quotation', string='Subscription State',
        help='State of the subscription', copy=False)
    subscription_orders = fields.Integer(string='Subscriptions',
                                         help='Subscription orders',
                                         compute='_compute_subscription_orders')
    payment_token_id = fields.Many2one(
        'payment.token', string='Payment Token',
        help='If a payment token is available, the subscription will automatically charge it upon invoice creation.',
        domain="[('partner_id', '=', partner_id)]")
    subscription_require_payment = fields.Boolean(
        string='Payment Token Required',
        help='Check if the subscription requires a payment token for automatic billing.')

    @api.depends('order_line')
    def _compute_is_subscription(self):
        """Check if subscription product is added or not"""
        for rec in self:
            rec.is_subscription = len(rec.order_line.filtered(
                lambda x: x.product_id.is_subscription)) > 0

    def _compute_subscription_orders(self):
        """
        Compute the number of subscription orders associated with the sale
        order and update related fields accordingly.
        :return: None
        """
        for rec in self:
            rec.subscription_orders = self.env[
                'subscription.order'].search_count(
                [('sale_order_id', '=', rec.id)])
            if rec.subscription_orders > 0:
                rec.state_subscription = 'sub_order'

    @api.onchange('sale_order_template_id')
    def _onchange_sale_order_template_id(self):
        """Change the renewal date when subscription plan changes"""
        res = super()._onchange_sale_order_template_id()
        for line in self.order_line:
            line.check_trial_period()
            line.price_unit = line.time_based_price_id.cost if line.time_based_price_id else 0.0
            subscription_unit = line.time_based_price_id.subscription_unit
            duration = line.time_based_price_id.duration if line.time_based_price_id else 0
            if subscription_unit in ('weeks', 'months', 'years'):
                delta = relativedelta(**{subscription_unit: duration})
                line.renewal_date = fields.Datetime.now() + delta
        return res

    def action_confirm(self):
        """Check if the order line has a subscription and non-subscription
                product if it is so needed to block it.
                Create subscription orders from each order line with subscription product"""

        sub_lines = self.order_line.filtered(lambda l: l.product_id.is_subscription)
        trial_discount_product = self.env.ref('cyllo_subscription.product_trial_discount',
                                              raise_if_not_found=False)
        non_allowed_lines = self.order_line.filtered(
            lambda l: not l.product_id.is_subscription and not (
                    getattr(l, "is_delivery",
                            False) and l.is_delivery or l.product_id == trial_discount_product))

        if sub_lines and non_allowed_lines:
            raise ValidationError(
                _('Cannot add subscription product with non-subscription product.'))

        for line in sub_lines:
            sub_order = self.env['subscription.order'].create({
                'partner_id': self.partner_id.id,
                'sale_order_id': self.id,
                'sale_order_line_id': line.id,
                'currency_id': self.currency_id.id,
                'sale_order_template_id': self.sale_order_template_id.id,
                'time_based_price_id': line.time_based_price_id.id,
                'end_date': line.end_date,
                'renewal_date': fields.Datetime.now(),
                'trial_end': fields.Datetime.now() if line.skip_trial else line.trial_end,
                'state': 'posted' if self.sale_order_template_id.invoice_creation else 'sale',
                'subscription_order_line_ids': [
                    fields.Command.create({
                        'product_id': line.product_id.id,
                        'time_based_price_id': line.time_based_price_id.id,
                        'quantity': line.product_uom_qty,
                        'tax_ids': line.tax_id.ids,
                        'subtotal': line.price_subtotal,
                        'total_price': line.price_total,
                    })
                ],
            })

            self.is_subscription = True
            self.state_subscription = 'sub_order'

            if sub_order.trial_end and sub_order.trial_end > fields.Datetime.now() and not line.skip_trial:
                sub_order.state_subscription = 'trial'
            else:
                sub_order.state_subscription = 'active'

            if self.sale_order_template_id.invoice_creation in ['draft', 'confirmed', 'sent']:
                sub_order.action_post()

        return super(SaleOrder, self).action_confirm()

    def action_subscriptions(self):
        """
        Open a window displaying subscription orders associated with the
        sale order.
        :return: Action dictionary to open the subscription orders window
        :rtype: dict
        """
        subscription_orders = self.env['subscription.order'].search(
            [('sale_order_id', '=', self.id)])
        return {
            'type': 'ir.actions.act_window',
            'name': _('Subscription Orders'),
            'res_model': 'subscription.order',
            'view_mode': 'tree,form',
            'target': 'current',
            'domain': [('id', 'in', subscription_orders.ids)]
        }
