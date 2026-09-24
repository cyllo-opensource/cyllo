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
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AccountPayment(models.Model):
    """Inheriting account.payment for adding new functionalities"""
    _inherit = 'account.payment'

    move_ids = fields.Many2many('account.move', help='Select Invoices')
    total_invoice_amount = fields.Monetary(currency_field='currency_id',
                                           compute='_compute_total_invoice_amount',
                                           store=True)
    payment_line_ids = fields.Many2many(comodel_name='account.payment.line', string='Invoices',
                                        help='Payment lines',
                                        compute='_compute_payment_line_ids', store=True,
                                        auto_join=True)
    total_payment_amount = fields.Monetary(
        "Total payment amount",
        compute='_compute_total_payment_amount',
        currency_field='company_currency_id'
    )
    multi_invoice_payment = fields.Boolean(default=False,
                                           help='If it is true then can choose multiple invoices for payment')

    batch_payment_id = fields.Many2one('batch.payment', string='Batch Payment',
                                       readonly=True)

    @api.depends('payment_line_ids', 'move_ids', 'move_ids.amount_residual', 'state')
    def _compute_total_invoice_amount(self):
        """Compute Total Invoice Amount"""
        for rec in self:
            if rec.state != 'posted':
                rec.total_invoice_amount = sum(rec.move_ids.mapped(
                    'amount_residual')) if rec.move_ids else 0
            else:
                rec.total_invoice_amount = sum(rec.payment_line_ids.mapped(
                    'paid_amount')) if rec.payment_line_ids else 0

    def _compute_total_payment_amount(self):
        """Calculate the total payment amount"""
        for rec in self:
            rec.total_payment_amount = rec.total_invoice_amount if rec.multi_invoice_payment else rec.amount_company_currency_signed

    @api.depends('amount', 'payment_type', 'total_payment_amount')
    def _compute_amount_signed(self):
        """Compute amount signed"""
        for payment in self:
            if payment.payment_type == 'outbound':
                payment.amount_signed = -payment.total_payment_amount if payment.multi_invoice_payment else -payment.amount
            else:
                payment.amount_signed = payment.total_payment_amount if payment.multi_invoice_payment else payment.amount

    @api.depends('move_ids', 'state', 'reconciled_invoice_ids')
    def _compute_payment_line_ids(self):
        """compute payment lines"""
        for rec in self:
            lines = []
            rec.payment_line_ids = False
            if rec.reconciled_invoice_ids:
                move_ids = rec.reconciled_invoice_ids
            elif rec.reconciled_bill_ids:
                move_ids = rec.reconciled_bill_ids
            else:
                move_ids = []
            for move in move_ids:
                payment_line = self.env['account.payment.line'].search([('move_id', '=', move.id),
                                                                        ('payment_id', '=',
                                                                         rec.id)], limit=1)
                if not payment_line:
                    payment_line = self.env['account.payment.line'].create({'move_id': move.id,
                                                                            'payment_id': rec.id})
                lines.append(payment_line.id)
            rec.payment_line_ids = [fields.Command.set(lines)]

    @api.onchange('partner_id', 'payment_type', 'is_internal_transfer')
    def _onchange_partner_id(self):
        """Generate user error if there is move_ids"""
        for rec in self:
            if not rec.partner_id or rec.is_internal_transfer:
                rec.multi_invoice_payment = False
            if rec.move_ids:
                raise UserError(_(
                    "\nThere are already some invoice lines."
                    "First remove the lines"))

    def action_draft(self):
        """Move to draft state"""
        res = super().action_draft()
        if self.move_ids:
            self.amount = 0
        for line in self.payment_line_ids:
            line.paid_amount = 0
        return res

    def action_confirm_invoice_payment(self):
        """If there is move_ids then only the confirm button calls this
         function"""
        if self.move_ids:
            payment = self._create_invoice_payment()
            if payment:
                for move in self.move_ids:
                    move.residual_amount = 0

    def payment_init(self, register_payment_id, to_process, edit_mode=False):
        """ Create the payments"""
        ref_string = ''
        for pay_line in self.move_ids:
            ref_string = ref_string + ' ' + pay_line.name
        for create_val in list(to_process[0].get('create_vals')):
            if create_val in self._fields and create_val not in ['ref']:
                self.write({create_val: to_process[0].get('create_vals')[create_val],
                            'ref': ref_string, 'amount': self.total_invoice_amount})
        payments = self
        for payment, vals in zip(payments, to_process):
            vals['payment'] = payment
            if edit_mode:
                lines = vals['to_reconcile']
                # Batches are made using the same currency so making
                # 'lines.currency_id' is ok.
                if payment.currency_id != lines.currency_id:
                    liquidity_lines, counterpart_lines, writeoff_lines = payment._seek_for_lines()
                    source_balance = abs(sum(lines.mapped('amount_residual')))
                    if liquidity_lines[0].balance:
                        payment_rate = liquidity_lines[0].amount_currency / liquidity_lines[
                            0].balance
                    else:
                        payment_rate = 0.0
                    source_balance_converted = abs(source_balance) * payment_rate
                    payment_balance = abs(sum(counterpart_lines.mapped('balance')))
                    payment_amount_currency = abs(sum(counterpart_lines.mapped('amount_currency')))
                    if not payment.currency_id.is_zero(
                            source_balance_converted - payment_amount_currency):
                        continue
                    delta_balance = source_balance - payment_balance
                    # Balance are already the same.
                    if register_payment_id.company_currency_id.is_zero(delta_balance):
                        continue
                    # Fix the balance but make sure to peek the liquidity and
                    # counterpart lines first.
                    debit_lines = (liquidity_lines + counterpart_lines).filtered('debit')
                    credit_lines = (liquidity_lines + counterpart_lines).filtered('credit')
                    if debit_lines and credit_lines:
                        payment.move_id.write({'line_ids': [
                            fields.Command.update(debit_lines[0].id,
                                                  {'debit': debit_lines[0].debit + delta_balance}),
                            fields.Command.update(credit_lines[0].id,
                                                  {'credit': credit_lines[
                                                                 0].credit + delta_balance}),
                        ]})
        return payments

    def payment_post(self, to_process, edit_mode=False):
        """ Post the newly created payments """
        payments = self.env['account.payment']
        for vals in to_process:
            vals['payment'] = self
            payments |= vals['payment']
        payments.action_post()

    def payment_reconcile(self, to_process, edit_mode=False):
        """ Reconcile the payments """
        domain = [('parent_state', '=', 'posted'),
                  ('account_type', 'in', ('asset_receivable', 'liability_payable')),
                  ('reconciled', '=', False)]
        for vals in to_process:
            payment_lines = vals['payment'].line_ids.filtered_domain(domain)
            payment_lines.write({'multi_invoice_payment': True})
            lines = vals['to_reconcile']
            for account in payment_lines.account_id:
                (payment_lines + lines).filtered_domain([('account_id', '=', account.id),
                                                         ('reconciled', '=', False)]).with_context(
                    multi_inv_payment=True).reconcile()

    def _create_invoice_payment(self):
        """For creating multiple invoice payment to one"""
        self.ensure_one()
        total_amt = 0
        for move in self.move_ids:
            if move.residual_amount == 0:
                total_amt += move.amount_residual
                move.residual_amount = move.amount_residual
            else:
                total_amt += move.residual_amount
        self.total_invoice_amount = total_amt
        register_payment_id = self.env['account.payment.register'].with_context(
            active_model='account.move', active_ids=self.move_ids.ids).create(
            {'journal_id': self.journal_id.id,
             'payment_method_line_id': self.payment_method_line_id.id,
             'partner_bank_id': self.partner_bank_id.id,
             'payment_date': self.date,
             'payment_type': self.payment_type,
             'communication': self.ref,
             'group_payment': True
             })
        batches = register_payment_id._get_batches()
        first_batch_result = batches[0]
        edit_mode = register_payment_id.can_edit_wizard and (
                len(first_batch_result['lines']) == 1 or register_payment_id.group_payment)
        to_process = []
        if edit_mode:
            payment_vals = register_payment_id._create_payment_vals_from_wizard(first_batch_result)
            to_process.append(
                {'create_vals': payment_vals, 'to_reconcile': first_batch_result['lines'],
                 'batch': first_batch_result})
        else:
            for batch_result in batches:
                to_process.append({
                                      'create_vals': register_payment_id._create_payment_vals_from_batch(
                                          batch_result),
                                      'to_reconcile': batch_result['lines'], 'batch': batch_result})
        payments = self.payment_init(register_payment_id, to_process, edit_mode=edit_mode)
        self.payment_post(to_process, edit_mode=edit_mode)
        self.payment_reconcile(to_process, edit_mode=edit_mode)
        return payments

    def button_open_statement_lines(self):
        """Redirect the user to the reconciled statement line(s) using the custom 'reconcile' view
        defined in the Cyllo module, instead of the default form or list view.

        :return: An action targeting the account.move model with the custom 'reconcile' view.
        """
        self.ensure_one()

        action = {
            'name': _("Matched Transactions"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.bank.statement.line',
            'context': {'create': False},
            'view_mode': 'reconcile',
        }
        if len(self.reconciled_statement_line_ids) == 1:
            action.update({
                'domain': [('id', '=', self.reconciled_statement_line_ids.id)],
            })
        else:
            action.update({
                'domain': [('id', 'in', self.reconciled_statement_line_ids.ids)],
            })
        return action