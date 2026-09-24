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


class SaleOrder(models.Model):
    """Extend the sale order line to add a field"""
    _inherit = 'sale.order'

    order_date = fields.Date(compute='_compute_order_date', store=True)
    is_paid = fields.Boolean(string='Paid', compute='_compute_is_paid',
                             store=True)
    payment_state = fields.Selection(selection=[
        ('not_paid', 'Not Paid'),
        ('partial_paid', 'Partially Paid'),
        ('paid', 'Paid'),
        ('partial_reversed', 'Partially Reversed'),
        ('reversed', 'Reversed')
    ],
        default='not_paid',
        compute='_compute_payment_state',
        store=True)

    amount_untaxed_latest = fields.Monetary(
        string='Untaxed Amount (Latest)',
        compute='_compute_amount_untaxed_latest',
        store=True,
        currency_field='currency_id'
    )

    @api.depends('date_order')
    def _compute_order_date(self):
        """Compute the order date from the date_order field."""
        for rec in self:
            rec.order_date = rec.date_order.date() if rec.date_order else False

    @api.depends('invoice_ids', 'invoice_ids.payment_state')
    def _compute_is_paid(self):
        """This function checks if the sale order is fully paid or not"""
        for rec in self:
            amount_to_invoice = rec.amount_total
            amount_invoiced = sum(rec.invoice_ids.filtered(
                lambda
                    p: p.payment_state == 'paid' and p.move_type == 'out_invoice').mapped(
                'amount_total'))
            rec.is_paid = False if amount_to_invoice - amount_invoiced > 0 else True

    @api.depends('invoice_ids', 'invoice_ids.payment_state',
                 'invoice_ids.amount_total')
    def _compute_payment_state(self):
        """The function helps to keep the selection field updated with correct status of the sale order about the payment status"""
        for rec in self:
            amount_to_invoice = rec.amount_total
            invoices = rec.invoice_ids.filtered(
                lambda inv: inv.state == 'posted')
            paid_invoices = invoices.filtered(lambda
                                                  inv: inv.move_type == 'out_invoice' and inv.payment_state == 'paid')
            paid_refunds = invoices.filtered(lambda
                                                 inv: inv.move_type == 'out_refund' and inv.payment_state == 'paid')
            paid_invoice_amount = sum(paid_invoices.mapped('amount_total'))
            paid_refund_amount = sum(paid_refunds.mapped('amount_total'))
            net_paid = paid_invoice_amount - paid_refund_amount

            if not invoices:
                rec.payment_state = 'not_paid'
            elif invoices and paid_invoice_amount and not paid_refund_amount:
                if amount_to_invoice - paid_invoice_amount > 0:
                    rec.payment_state = 'partial_paid'
                elif amount_to_invoice - paid_invoice_amount <= 0:
                    rec.payment_state = 'paid'
            elif paid_refund_amount:
                if not net_paid:
                    rec.payment_state = 'reversed'
                elif net_paid < amount_to_invoice:
                    rec.payment_state = 'partial_reversed'

    @api.depends('order_line.price_subtotal_latest')
    def _compute_amount_untaxed_latest(self):
        """Compute the latest untaxed amount based on the order lines."""
        for order in self:
            order = order.with_company(order.company_id)
            order_lines = order.order_line.filtered(
                lambda l: not l.display_type)

            if order.company_id.tax_calculation_rounding_method == 'round_globally':
                subtotal = sum(order_lines.mapped('price_subtotal_latest'))
                order.amount_untaxed_latest = order.currency_id.round(subtotal)
            else:
                subtotal = sum(
                    order.currency_id.round(line.price_subtotal_latest) for line
                    in order_lines)
                order.amount_untaxed_latest = subtotal
