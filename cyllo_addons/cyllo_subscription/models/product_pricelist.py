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


class Pricelist(models.Model):
    """ Extends the product pricelist to support time-based subscription pricing."""
    _inherit = "product.pricelist"

    subscription_pricing_ids = fields.One2many(
        comodel_name='subscription.pricing',
        inverse_name='pricelist_id',
        string="Time Based Price Rules",
        copy=True)


    def _get_time_based_price_rule(self,product_template_id,subscription_unit,duration,date,product_uom_qty):
        """Search for the most suitable subscription pricing rule based on the provided criteria.
                :param int product_template_id: The ID of the product template to price.
                :param str subscription_unit: The time unit (e.g., 'daily', 'monthly', 'yearly').
                :param int duration: The length of the subscription.
                :param date date: The reference date for rule validity (usually today).
                :param float product_uom_qty: The quantity being ordered to match min_quantity rules.
                :return: recordset of 'subscription.pricing' (limit 1) or empty recordset."""

        suitable_price_rule = self.env['subscription.pricing'].sudo().search([
            ('id', 'in', self.sudo().subscription_pricing_ids.ids),
            ('product_tmpl_id', '=', product_template_id),
            ('subscription_unit', '=', subscription_unit),
            ('duration', '=', duration),
            '|', ('date_start', '=', False), ('date_start', '<=', date),
            '|', ('date_end', '=', False), ('date_end', '>=', date),
            ('min_quantity', '<=', product_uom_qty)], order='min_quantity desc', limit=1)
        return suitable_price_rule

    def _get_subscription_price(self, product_template_id, plan, quantity=1.0, date=None):
        """
        Compute the subscription price for a given product and plan.
        1. Checks for a specific Time-Based Pricing Rule in this pricelist.
        2. If no rule, falls back to the plan's cost converted to pricelist currency.
        :param product_template_id: int
        :param plan: time.based.price record
        :param quantity: float
        :param date: datetime or date
        :return: float (price)
        """
        if not date:
            date = fields.Date.today()
        
        rule = self._get_time_based_price_rule(
            product_template_id, 
            plan.subscription_unit, 
            plan.duration, 
            date, 
            quantity
        )
        
        if rule:
            return rule.fixed_price
            
        return plan.currency_id._convert(
            plan.cost,
            self.currency_id,
            self.company_id or self.env.company,
            date
        )



