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
from odoo import models, fields

class ProductTemplate(models.Model):
    """Inherits product template to override variant information retrieval,
    integrating time-based pricing and currency-converted
    tax calculations into the standard website price display."""
    _inherit = 'product.template'

    def _get_combination_info(self, combination=False, product_id=False, add_qty=1.0,
                              parent_combination=False, **kwargs):
        """Overrides combination info to inject time based pricing and subscription pricing rule into the frontend,
        calculating tax-adjusted prices based on selected time based price and active pricelists."""
        # Call super to get the context, currency, and tax objects
        res = super(ProductTemplate, self)._get_combination_info(
            combination=combination, product_id=product_id, add_qty=add_qty,
            parent_combination=parent_combination)

        # Identify the Subscription Plan
        plan_id = kwargs.get('plan_id')
        if not plan_id and self.is_subscription and self.sudo().time_based_ids:

            plan_id = self.time_based_ids[:1].id

        if plan_id and str(plan_id).isdigit():
            plan = self.env['time.based.price'].sudo().browse(int(plan_id))
            if plan.exists():
                # Handle Currency Conversion
                website = self.env['website'].get_current_website()
                pricelist = website.pricelist_id
                website_currency = pricelist.currency_id or website.currency_id

                time_based_price_rule = pricelist._get_time_based_price_rule(
                        self.id, plan.subscription_unit, plan.duration,
                        fields.Datetime.now(), add_qty
                    )
                
                # Use unified method for price calculation
                price = pricelist._get_subscription_price(
                    self.id,
                    plan,
                    add_qty,
                    fields.Date.today()
                )

                # Apply Taxes manually
                # We use the taxes already calculated by super() in res['product_taxes']
                # and res['taxes'] (which handles fiscal positions).
                if res.get('taxes'):
                    price = self._apply_taxes_to_price(
                        price,
                        website_currency,
                        res['product_taxes'],
                        res['taxes'],
                        self.env['product.product'].browse(res['product_id']) or self
                    )

                #  Update the response
                # Now 'price' and 'list_price' contain the tax-adjusted values
                res.update({
                    'price': price,
                    'list_price': price,
                    'currency': website_currency,
                    'is_subscription': True,
                    'sub_pricing_id': plan.id,
                })

        return res

    def _search_render_results(self, fetch_fields, mapping, icon, limit):
        """Append the subscription duration to the price in the search bar autocomplete dropdown."""
        # Get the standard search results
        results_data = super()._search_render_results(fetch_fields, mapping, icon, limit)

        # Loop through the matching products and their formatted dictionary data
        for product, data in zip(self, results_data):
            if product.is_subscription and product.sudo().time_based_ids and 'price' in data:
                plan = product.sudo().time_based_ids[0]

                if plan.duration == 1:
                    unit_str = plan.subscription_unit.capitalize().rstrip('s')
                else:
                    unit_str = f"{plan.duration} {plan.subscription_unit.capitalize()}"
                data[
                    'price'] = f"{data['price']} <span style='font-weight: normal; font-size: 0.9em;' class='text-muted'>/ {unit_str}</span>"

        return results_data

