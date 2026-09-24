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
from odoo.exceptions import UserError


class AccountMove(models.Model):
    """Inheriting account.move for adding installment related fields
    and functions for computing installments."""
    _inherit = 'account.move'

    installment_payment = fields.Boolean(string='Apply Installment',
                                         default=False,
                                         help='Enable installment payment')
    total_installment_amount = fields.Float(string='Total Amount',
                                            help='Total invoice Amount to pay')
    advance_payment_amount = fields.Float(help='Advance for installment')
    installment_due_amount = fields.Float(string='Total Installment Amount',
                                          help='Amount due for installment')
    installment_amount = fields.Float(help='amount for one period')
    installment_paid = fields.Float(help='Installment Paid Amount',
                                    compute='_compute_installment_paid',
                                    store=True)
    installment_to_pay = fields.Float(help='Installment Amount to Pay',
                                      compute='_compute_installment_paid',
                                      store=True)
    next_installment_date = fields.Date('Next Installment Date',
                                        help='Next date for paying installment',
                                        compute='_compute_installment_paid',
                                        store=True)
    duration = fields.Integer(string='Duration(Months)', default=5,
                              help='duration of installment in months')
    installment_ids = fields.One2many('account.installment',
                                      string='Installments',
                                      inverse_name="move_id",
                                      help="Created Installments", copy=False)
    # To show the advance payment amounts in reports.
    #     advance payments calculating in cyllo_advance_payment module
    advance_payment_ids = fields.One2many('account.payment',
                                          string='Advance Payments',
                                          compute='_compute_advance_payment_ids')
    total_advance_paid_amount = fields.Float(
        compute='_compute_advance_payment_ids')

    def _compute_advance_payment_ids(self):
        """Find Advance Payments related to the invoice """
        for rec in self:
            rec.advance_payment_ids = False
            source_sale_orders = rec.line_ids.sale_line_ids.order_id
            source_purchase_orders = rec.line_ids.purchase_line_id.order_id
            if source_sale_orders:
                rec.advance_payment_ids = self.env['account.payment'].search(
                    [('reconciled_invoice_ids', 'in', rec.id),
                     ('sale_id', 'in', source_sale_orders.ids)])
            elif source_purchase_orders:
                rec.advance_payment_ids = self.env['account.payment'].search(
                    [('purchase_id', 'in', source_purchase_orders.ids),
                     ('reconciled_bill_ids', '=', rec.id)])
            rec.total_advance_paid_amount = sum(
                rec.advance_payment_ids.mapped(
                    'amount')) if rec.advance_payment_ids else 0

    @api.depends('installment_ids', 'installment_ids.pay_amount',
                 'installment_ids.state')
    def _compute_installment_paid(self):
        """Compute installment values"""
        for rec in self:
            rec.installment_paid = 0
            rec.installment_to_pay = 0
            unpaid_installment_ids = rec.installment_ids.filtered(
                lambda x: x.state == 'draft').sorted(key=lambda l: l.sequence)
            rec.next_installment_date = unpaid_installment_ids[
                0].payment_date if unpaid_installment_ids else False
            for installment in rec.installment_ids:
                if installment.state == 'draft':
                    rec.installment_to_pay += installment.pay_amount
                else:
                    rec.installment_paid += installment.pay_amount

    def _compute_installment_dates(self):
        """Find the installment dates"""
        due_date = self.invoice_date_due if self.invoice_date_due else fields.Date.today()
        installment_dates = []
        for i in range(1, self.duration + 1):
            next_date = due_date + relativedelta(months=i)
            installment_dates.append(next_date)
        return installment_dates

    def _generate_installments(self):
        """Generate installments for the invoice"""
        if self.amount_residual > 0:
            if self.amount_residual < self.advance_payment_amount:
                raise UserError(
                    _("The Advance amount is greater than the total amount to pay"))
            self.installment_due_amount = self.amount_residual - self.advance_payment_amount
            self.total_installment_amount = self.amount_residual
            if self.duration > 0:
                self.installment_amount = self.installment_due_amount / self.duration
            else:
                raise UserError(_("The duration cannot be zero or negative"))
            if self.installment_ids:
                self.installment_ids.unlink()
            start_date = self.date if self.date else fields.Date.today()
            due_date = self.invoice_date_due if self.invoice_date_due else fields.Date.today()
            seq = 1
            installment_count = 1
            if self.advance_payment_amount > 0:
                self.env['account.installment'].create({
                    'sequence': seq,
                    'name': 'Advance Amount',
                    'payment_date': start_date,
                    'is_advance': True,
                    'pay_amount': self.advance_payment_amount,
                    'move_id': self.id,
                })
                seq += 1
            for i in range(1, self.duration + 1):
                next_date = due_date + relativedelta(months=i)
                self.env['account.installment'].create({
                    'sequence': seq,
                    'name': str(installment_count) + ' Installment Amount',
                    'payment_date': next_date,
                    'is_advance': False,
                    'pay_amount': self.installment_amount,
                    'move_id': self.id,
                })
                installment_count += 1
                seq += 1
            total_installment_amount = sum(
                round(installemnt.pay_amount, 2) for installemnt in
                self.installment_ids)
            last_installment = self.installment_ids[-1]
            if self.amount_residual > total_installment_amount:
                last_installment.pay_amount += round(
                    self.amount_residual - total_installment_amount, 2)
            elif self.amount_residual < total_installment_amount:
                last_installment.pay_amount -= round(
                    total_installment_amount - self.amount_residual, 2)

    def action_post(self):
        """When confirming invoice creates installments"""
        res = super(AccountMove, self).action_post()
        if self.installment_payment:
            if self.installment_ids:
                self.installment_ids.unlink()
            self._generate_installments()
            for installment in self.installment_ids:
                installment.ready_to_pay = True
        return res

    def button_cancel(self):
        """Button: Cancel"""
        res = super(AccountMove, self).button_cancel()
        for installment in self.installment_ids:
            installment.write({
                'state': 'cancel'
            })
        return res

    def button_draft(self):
        """Button: Reset to Draft"""
        res = super(AccountMove, self).button_draft()
        for installment in self.installment_ids:
            installment.ready_to_pay = False
        return res

    def action_button_compute_installments(self):
        """Button: Compute Installments"""
        if self.installment_payment:
            self._generate_installments()
