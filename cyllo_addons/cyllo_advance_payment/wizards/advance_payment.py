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
from datetime import datetime

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AdvancePayment(models.TransientModel):
    """Wizard for Advance Payment"""
    _name = 'advance.payment'
    _description = 'Advance Payment'

    communication = fields.Char(string="Memo", help="Reference")
    pay_amount = fields.Float(string="Advance Pay Amount", help="Advance amount"
                                                                " to pay")
    total_amount = fields.Float(help="Total Amount from the order")
    amount_difference = fields.Float(help="Difference between total amount and"
                                          " advance amount")
    currency_id = fields.Many2one(comodel_name="res.currency", readonly=True)
    partner_id = fields.Many2one(comodel_name="res.partner")
    date = fields.Datetime(string="Payment Date")
    company_id = fields.Many2one("res.company")
    journal_id = fields.Many2one(comodel_name="account.journal", compute="_compute_journal_id", store=True,
                                 readonly=False, precompute=True, check_company=True, help="Journal for the payment")
    payment_method_line_id = fields.Many2one('account.payment.method.line', string='Payment Method',
                                             store=True, compute='_compute_payment_method_line_id',
                                             help="Payment method line for the payment")

    def default_get(self, fields_list):
        """Default values to the wizard"""
        res = super(AdvancePayment, self).default_get(fields_list)
        res.update({"currency_id": self.env.user.company_id.currency_id.id, "company_id": self.env.user.company_id.id})
        if self._context.get("type") == 'sale':
            active_id = self.env["sale.order"].browse(self._context.get("active_id"))
        else:
            active_id = self.env["purchase.order"].browse(self._context.get("active_id"))
        if active_id:
            if active_id.invoice_status != 'invoiced':
                res.update({
                    "communication": active_id.name,
                    "total_amount": active_id.amount_total - active_id.total_advance_amount,
                    "pay_amount": active_id.amount_total - active_id.total_advance_amount,
                    "partner_id": active_id.partner_id.id,
                    "currency_id": active_id.currency_id.id if active_id.currency_id
                    else self.env.user.company_id.currency_id.id,
                    "company_id": active_id.company_id.id if active_id.company_id else self.env.user.company_id.id,
                    "date": datetime.now(),
                })
            else:
                res.update({"communication": active_id.name, "pay_amount": 0,
                            "total_amount": active_id.amount_total - active_id.total_advance_amount})
        return res

    @api.depends('company_id')
    def _compute_journal_id(self):
        """Compute the default journal based on company"""
        for wizard in self:
            domain = [
                *self.env['account.journal']._check_company_domain(wizard.company_id),
                ('type', 'in', ('bank', 'cash'))
            ]
            wizard.journal_id = self.env['account.journal'].search(domain, limit=1)

    def _compute_total_amount(self):
        """Compute the total amount and payment amount for the current record.
           This method computes the total amount and payment amount based on the active record's context type
           ('sale' or 'purchase').For sales, it retrieves the active sale order and calculates the total amount by
           deducting the sum of existing advance payments.
           For purchases, it retrieves the active purchase order and calculates the total amount similarly."""
        if self._context.get("type") == 'sale':
            active_id = self.env["sale.order"].browse(self._context.get("active_id"))
            existing_advance_payment_ids = self.env["account.payment"].search([('sale_id', '=', active_id.id)])
        else:
            active_id = self.env["purchase.order"].browse(self._context.get("active_id"))
            existing_advance_payment_ids = self.env["account.payment"].search([('purchase_id', '=', active_id.id)])
        for rec in self:
            rec.total_amount = active_id.amount_total - sum(existing_advance_payment_ids.mapped('amount')) \
                if existing_advance_payment_ids else active_id.amount_total
            rec.pay_amount = rec.total_amount

    @api.depends('journal_id')
    def _compute_payment_method_line_id(self):
        """Compute the payment method line based on the journal"""
        for wizard in self:
            if wizard.journal_id:
                if self._context.get("type") == 'sale':
                    available_payment_method_lines = wizard.journal_id._get_available_payment_method_lines('inbound')
                else:
                    available_payment_method_lines = wizard.journal_id._get_available_payment_method_lines('outbound')
            else:
                available_payment_method_lines = False

            # Select the first available one by default.
            if available_payment_method_lines:
                wizard.payment_method_line_id = available_payment_method_lines[0]._origin
            else:
                wizard.payment_method_line_id = False

    @api.onchange("pay_amount")
    def _onchange_pay_amount(self):
        """Find amount difference when changing the field pay_amount"""
        if self.pay_amount > self.total_amount:
            raise UserError(_("The Advance amount is greater than the total amount to pay"))
        self.amount_difference = self.total_amount - self.pay_amount

    def action_validate_payment(self):
        """Button: Advance Payment , Creates new payment with wizard values"""
        if self._context.get("type") == 'sale':
            active_id = self.env["sale.order"].browse(self._context.get("active_id"))
        else:
            active_id = self.env["purchase.order"].browse(self._context.get("active_id"))
        if active_id:
            self.env['account.payment'].create({
                'partner_id': active_id.partner_id.commercial_partner_id.id,
                'company_id': self.env.user.company_id.id,
                'date': self.date,
                'amount': self.pay_amount,
                'currency_id': self.currency_id.id,
                'payment_type': 'inbound' if self._context.get("type") == 'sale' else 'outbound',
                'partner_type': 'customer' if self._context.get("type") == 'sale' else 'supplier',
                'sale_id': self._context.get("active_id") if self._context.get("type") == 'sale' else False,
                'purchase_id': self._context.get("active_id") if self._context.get("type") == 'purchase' else False,
                'journal_id': self.journal_id.id,
                'payment_method_line_id': self.payment_method_line_id.id,
                'ref': _("%s - Advance Payment", active_id.name),
            }).action_post()
