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
from odoo import models
from odoo.exceptions import ValidationError


class SaleOrder(models.Model):
    """Inherited Sale Order model to add custom functionality for merging
    quotations."""
    _inherit = 'sale.order'

    def action_merge_quotation(self):
        """Merge selected sale orders with the same partner and in the
        quotation state. Creates a new sale order, consolidates order lines,
        and deletes the original orders. Redirects to the form view of the
        newly created sale order.
        :return: Action dictionary for redirection.
        :rtype: dict"""
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
            raise ValidationError(
                "Please select orders in the quotation state.")
        new_sale_order = self.create({"partner_id": reference_partner_id})
        order_lines = {}
        for order in self:
            for line in order.order_line:
                key = (line.product_id.id, line.price_unit / order.currency_rate)
                if key in order_lines:
                    order_line = order_lines[key]
                    price = order_line.price_unit
                    order_line.product_uom_qty += line.product_uom_qty
                    order_line.price_unit = price
                else:
                    order_lines[key] = line.copy(
                        default={
                            "order_id": new_sale_order.id,
                            "price_unit": line.price_unit / order.currency_rate,
                        })
        self.unlink()
        return {
            'view_mode': 'form',
            'res_model': 'sale.order',
            'res_id': new_sale_order.id,
            'type': 'ir.actions.act_window',
            'target': 'current',
        }
