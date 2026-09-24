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

from odoo import api, fields, models,_
from odoo.exceptions import ValidationError


class SaleOrderLine(models.Model):
    """Inherited the model to add some fields and methods"""
    _inherit = 'sale.order.line'

    time_based_price_id = fields.Many2one('time.based.price', string='Time Based Pricing',
                                          default=lambda self: self.product_template_id.time_based_ids[0]
                                          if self.product_template_id.time_based_ids else False,
                                          domain="[('product_template_id', 'in', [product_template_id])]",
                                          help='Field shows the recurrence of the product', copy=False)
    renewal_date = fields.Datetime(help='Renewal date for the subscription order created from this line', copy=False)
    trial_end = fields.Datetime(help='Trial end date for the subscription order created from this line.', copy=False)
    end_date = fields.Datetime(string='End Date', copy=False)
    skip_trial = fields.Boolean(default=False, string="Skip Trial", help="If set, trial period will be skipped for this line.", copy=False)

    @api.depends('time_based_price_id', 'product_uom_qty')
    def _compute_price_unit(self):
        """ Compute the unit price for subscription-based products.
        This method overrides the default price computation to look up
        specific time-based pricing rules from the pricelist. If no
        rule is found, it falls back to the plan's default cost."""
        super()._compute_price_unit()

        for line in self:
            if line.product_template_id.is_subscription and line.time_based_price_id:
                plan = line.time_based_price_id
                order = line.order_id
                price_unit = order.pricelist_id._get_subscription_price(
                    line.product_template_id.id,
                    plan,
                    line.product_uom_qty,
                    order.date_order
                )
                line.price_unit = price_unit

    @api.constrains('end_date')
    def _check_end_date(self):
        """Validate that the subscription end date is not in the past relative to the order date.
        raises ValidationError: If the end date is before the order creation date."""
        for record in self:
            if record.end_date and record.end_date < record.order_id.date_order:
                raise ValidationError(
                    _("Invalid End Date: The subscription end date cannot be prior to the order date."))

    @api.constrains('trial_end')
    def _check_trial_end_date(self):
        """Validate that the trial end date is not in the past."""
        for record in self:
            if record.trial_end and record.trial_end.date() < fields.Date.today():
                raise ValidationError(_("The trial end date cannot be set in the past."))

    @api.onchange('time_based_price_id', 'product_uom_qty')
    def _onchange_time_based_price_id(self):
        """Change price when change the time-based pricing"""
        if self.time_based_price_id:
            plan = self.time_based_price_id
            order = self.order_id
            # Need to handle NewId in onchange
            if order.id:
                date_order = order.date_order
            else:
                date_order = fields.Datetime.now()

            self.price_unit = order.pricelist_id._get_subscription_price(
                self.product_template_id.id._origin if hasattr(self.product_template_id.id,
                                                               '_origin') else self.product_template_id.id,
                plan,
                self.product_uom_qty,
                date_order
            )
        else:
             # Fallback to standard price if no time based id (though it's required for sub products?)
             pass
        self.check_trial_period()
        if self.time_based_price_id:
            if self.time_based_price_id.subscription_unit == 'weeks':
                self.renewal_date = fields.Datetime.now() + relativedelta(weeks=self.time_based_price_id.duration)
            elif self.time_based_price_id.subscription_unit == 'months':
                self.renewal_date = fields.Datetime.now() + relativedelta(months=self.time_based_price_id.duration)
            elif self.time_based_price_id.subscription_unit == 'years':
                self.renewal_date = fields.Datetime.now() + relativedelta(years=self.time_based_price_id.duration)

    @api.onchange('product_id')
    def _onchange_product_id(self):
        """When a product is added default value to time_based_price_id field
        is the first value from the time-based-price model in products"""
        if self.product_template_id.time_based_ids:
            self.time_based_price_id = self.product_template_id.time_based_ids[0]


    @api.onchange('skip_trial')
    def _onchange_skip_trial(self):
        """Update trial period when skip trial is toggled manually."""
        self.check_trial_period()

    def check_trial_period(self):
        """Check if any trial-period is added in product template"""
        if self.skip_trial:
            self.trial_end = False
            return

        plan = self.time_based_price_id
        if plan and plan.trial_period > 0:
            history_exists = self.env['subscription.trial.history'].search([
                ('partner_id', '=', self.order_id.partner_id.id),
                ('time_based_price_id', '=', plan.id)
            ], limit=1)
            if history_exists:
                self.trial_end = fields.Datetime.now()
            else:
                if plan.trial_unit == 'days':
                    self.trial_end = fields.Datetime.now() + relativedelta(days=plan.trial_period)
                elif plan.trial_unit == 'weeks':
                    self.trial_end = fields.Datetime.now() + relativedelta(weeks=plan.trial_period)
                elif plan.trial_unit == 'months':
                    self.trial_end = fields.Datetime.now() + relativedelta(months=plan.trial_period)
                else:
                    self.trial_end = fields.Datetime.now()
        else:
            self.trial_end = fields.Datetime.now()


