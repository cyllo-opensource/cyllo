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


class SaleOrderLine(models.Model):
    """Extend Order lines to add fields"""
    _inherit = 'sale.order.line'

    price_subtotal_latest = fields.Float(string='Price Subtotal',
                                         compute='_compute_price_subtotal_latest',
                                         store=True)

    @api.depends('order_id.invoice_ids', 'order_id.invoice_ids.payment_state',
                 'order_id.invoice_ids.amount_total')
    def _compute_price_subtotal_latest(self):
        """This function compute the price of the order-line product .
        Basically the field value will be the same as price_subtotal and
        when the product is returned the returned price_subtotal will be deducted from the price.
        Helps to keep the correct price of sale from the sale order itself"""
        for rec in self:
            rec.price_subtotal_latest = rec.price_subtotal or 0.0
            refund_invoices = rec.order_id.invoice_ids.filtered(
                lambda
                    r: r.move_type == 'out_refund' and r.payment_state in ['paid', 'partial'])
            refund_lines = refund_invoices.mapped('invoice_line_ids').filtered(
                lambda l: l.product_id == rec.product_id
            )
            for line in refund_lines:
                rec.price_subtotal_latest -= line.price_subtotal or 0.0
