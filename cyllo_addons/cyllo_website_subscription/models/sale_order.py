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
from odoo import _,models,fields
from odoo.exceptions import ValidationError

class SaleOrder(models.Model):
    """Extends sale orders to manage ecommerce sunscription sale."""
    _inherit = 'sale.order'

    def _compute_amounts(self):
        """Recalculate trial line before final totals."""
        for order in self:
            if order.website_id:
                order._set_trial_discount_line()
        return super()._compute_amounts()

    def action_confirm(self):
        if self.website_id:
            res = super().action_confirm()
            subscription_orders = self.env['subscription.order'].search(
                    [('sale_order_id', '=', self.id)])
            for sub_order in subscription_orders:
                sub_order.action_post()
            return res
        return super().action_confirm()



    def _get_subscription_trial_offset(self):
        """Calculates total value of trial items for display masking by reading the generated discount lines."""
        trial_discount_product = self.env.ref('cyllo_subscription.product_trial_discount', raise_if_not_found=False)
        if not trial_discount_product:
            return 0.0, 0.0, 0.0

        trial_discount_lines = self.order_line.filtered(lambda l: l.product_id == trial_discount_product)
        price_total = abs(sum(trial_discount_lines.mapped('price_total')))
        price_subtotal = abs(sum(trial_discount_lines.mapped('price_subtotal')))
        tax_total = abs(sum(trial_discount_lines.mapped('price_tax')))
        return price_total, tax_total, price_subtotal


    def _cart_find_product_line(self, product_id, line_id=None, **kwargs):
        """ Find the cart line matching the product AND the selected plan """
        lines = super()._cart_find_product_line(product_id, line_id, **kwargs)

        # If we are looking for a specific plan from the website
        plan_id = kwargs.get('time_based_price_id')

        if plan_id:
            # Filter the lines to find one that has the SAME plan
            lines = lines.filtered(lambda l: l.time_based_price_id.id == int(plan_id))
        elif not line_id:
            # If no plan is passed, only match lines that HAVE NO plan
            lines = lines.filtered(lambda l: not l.time_based_price_id)

        return lines

    def _set_trial_discount_line(self):
        """Create or update trial discount lines."""

        trial_product = self.env.ref(
            'cyllo_subscription.product_trial_discount',
            raise_if_not_found=False,
        )
        if not trial_product:
            return

        trial_sub_lines = self.order_line.filtered(
            lambda l: (
                    l.product_id.is_subscription
                    and l.trial_end
                    and l.trial_end > fields.Datetime.now()
            )
        )

        groups = {}

        for line in trial_sub_lines:
            plan = line.time_based_price_id
            # Calculate discount amount based on pricing type (for 1 quantity)
            sub_total = line.price_subtotal
            discount_amount = 0.0

            if not plan.trial_pricing_type or plan.trial_pricing_type == 'free':
                discount_amount = sub_total
            elif plan.trial_pricing_type == 'fixed_price':
                trial_total = plan.trial_value* line.product_uom_qty
                discount_amount = max(sub_total - trial_total , 0.0)
            elif plan.trial_pricing_type == 'percentage_discount':
                discount_amount = sub_total * (plan.trial_percentage / 100.0)

            if discount_amount <= 0:
                continue

            if trial_product.id not in groups:
                groups[trial_product.id] = {
                    'product': trial_product,
                    'amount': 0.0,
                    'taxes': line.tax_id,
                }
            else:
                groups[trial_product.id]['taxes'] |= line.tax_id

            groups[trial_product.id]['amount'] += discount_amount

        # Check if existing discount lines already match exactly to avoid recursive creation in _compute_amounts
        existing_lines = self.order_line.filtered(
            lambda l: l.product_id == trial_product
                      or l.product_id.id in groups.keys()
        )

        # Determine if an update is really needed
        needs_update = False
        if len(existing_lines) != len(groups):
            needs_update = True
        else:
            for line in existing_lines:
                group = groups.get(line.product_id.id)
                if not group or line.price_unit != -group['amount'] or set(line.tax_id.ids) != set(group['taxes'].ids):
                    needs_update = True
                    break

        if not needs_update:
            return

        # Update existing trial discount lines or create new ones
        for product_id, values in groups.items():
            matching_lines = existing_lines.filtered(lambda l: l.product_id.id == product_id)
            if matching_lines:
                line_to_update = matching_lines[0]
                line_to_update.sudo().write({
                    'price_unit': -values['amount'],
                    'tax_id': [(6, 0, values['taxes'].ids)],
                })
                existing_lines -= line_to_update
            else:
                product = values['product']
                # line_name = product.description_sale or product.name or 'Trial Discount'
                self.env['sale.order.line'].sudo().create({
                    'order_id': self.id,
                    'product_id': product.id,
                    'name': 'Trial Discount',
                    'product_uom_qty': 1,
                    'price_unit': -values['amount'],
                    'tax_id': [(6, 0, values['taxes'].ids)],
                    'sequence': 999,
                })

        # Remove any remaining lines that are no longer needed
        if existing_lines:
            existing_lines.unlink()




