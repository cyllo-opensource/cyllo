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
from odoo.exceptions import ValidationError


class PurchaseOrder(models.Model):
    """
        Inherited Purchase Order model to add custom functionality for merging
        RFQ.
    """
    _inherit = 'purchase.order'

    is_global_discount = fields.Boolean(
        string='Global Discount', help="If enabled it allows to add global "
                                       "discount for the purchase order")
    discount_type = fields.Selection(
        string='Discount types', help="Choose the discount type",
        selection=[('amount', 'Amount'), ('percentage', 'Percentage')])
    discount_amount = fields.Float(
        string="Discount in Amount", help="Enter the discount rate")
    discount_percentage = fields.Float(
        string="Discount in Percentage", help="Enter the discount percentage")

    def action_merge_rfq(self):
        """
            Merge selected RFQ with the same partner and in the draft state.
            Creates a new RFQ, consolidates order lines, and deletes the original
             orders. Redirects to the form view of the newly created RFQ.
            :return: Action dictionary for redirection.
            :rtype: dict
        """
        if len(self) < 2:
            raise ValidationError(
                "Please select at least two orders to merge.")
        reference_partner_id = self[0].partner_id.id
        reference_company_id = self[0].company_id.id
        if any(order.partner_id.id != reference_partner_id for order in self):
            raise ValidationError("Selected orders have different partners.")
        if any(order.company_id.id != reference_company_id for order in self):
            raise ValidationError("Selected orders have different company.")
        if any(order.state != 'draft' for order in self):
            raise ValidationError("Please select orders in the RFQ state.")
        new_purchase_order = self.env['purchase.order'].create(
            {"partner_id": reference_partner_id})
        order_lines = {}
        for order in self:
            for line in order.order_line:
                key = (line.product_id.id, line.price_unit / order.currency_rate)
                if key in order_lines:
                    order_line = order_lines[key]
                    price = order_line.price_unit / order.currency_rate
                    order_line.product_qty += line.product_qty
                    order_line.price_unit = price
                else:
                    new_line = line.copy(
                        default={
                            "order_id": new_purchase_order.id,
                            "price_unit": line.price_unit / order.currency_rate,
                        })
                    order_lines[key] = new_line
        self.sudo().button_cancel()
        self.sudo().unlink()
        return {
            'view_mode': 'form',
            'res_model': 'purchase.order',
            'res_id': new_purchase_order.id,
            'type': 'ir.actions.act_window',
            'target': 'current',
        }

    def action_apply_discount(self):
        """
            Apply a global discount to all order lines.

            - If discount type is 'percentage', the same percentage is applied
              to all order lines.
            - If discount type is 'fixed amount', the given discount amount is
              proportionally distributed across all order lines based on each
              line's subtotal.The proportional discount amount for each line is
              converted into an equivalent percentage.
            - If either `discount_amount` or `amount_total` is zero, no discount
              is applied and all order line discounts are reset to 0.
        """
        if self.discount_type == 'percentage':
            discount_in_percentage = self.discount_percentage
            for line in self.order_line:
                line.discount = discount_in_percentage
        else:
            if self.discount_amount > 0 and self.amount_total > 0:
                total_discount = self.discount_amount
                total_untaxed = sum(
                    (line.price_unit * line.product_qty) for line in
                    self.order_line)
                if total_untaxed > 0:
                    for line in self.order_line:
                        line_discount_amount = (line.price_subtotal / total_untaxed) * total_discount
                        line.discount = (line_discount_amount / line.price_subtotal * 100) if line.price_subtotal > 0 else 0
            else:
                for line in self.order_line:
                    line.discount = 0
