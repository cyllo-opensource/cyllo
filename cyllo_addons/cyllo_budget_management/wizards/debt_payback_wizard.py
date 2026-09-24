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
from odoo.exceptions import ValidationError


class DebtPaybackWizard(models.TransientModel):
    """ Model used to perform Payment and debt related functions """

    _name = 'debt.payback.wizard'
    _description = "Wizard for the payback Details in Debt"

    available_journal_ids = fields.Many2many(
        'account.journal', compute='_compute_available_journal_ids')
    journal_id = fields.Many2one(
        'account.journal', domain="[('id', 'in', available_journal_ids)]",
        required=True, help='Choose the journal')
    payment_method_line_id = fields.Many2one(
        'account.payment.method.line', string='Payment Method',
        domain="[('id', 'in', payment_method_line_ids)]", required=True,
        help='Choose the Payment Method')
    payment_method_line_ids = fields.Many2many(
        'account.payment.method.line',
        compute='_compute_payment_method_line_ids')
    partner_id = fields.Many2one('res.partner')
    payback_partner_id = fields.Many2one('res.partner')
    recipient_bank_id = fields.Many2one(
        'res.partner.bank', domain="[('partner_id','=',partner_id)]",
        help='Choose the bank')
    payback_recipient_bank_id = fields.Many2one(
        'res.partner.bank', string='Recipient Bank',
        domain="[('partner_id','=',payback_partner_id)]",
        help='Choose the bank')
    debt_id = fields.Many2one('debt.management')
    return_type = fields.Selection(
        selection=[('partial', 'Partially'), ('full', 'Completely')],
        default='full', help='Choose the Type')
    amount = fields.Monetary(help='Amount', currency_field='currency_id')
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.user.company_id.currency_id.id)
    balance_amount = fields.Monetary(
        string='Balance', help='Balance to payback',
        currency_field='currency_id')
    company_id = fields.Many2one('res.company',
                                 default=lambda self: self.env.company.id)

    @api.depends('company_id')
    def _compute_available_journal_ids(self):
        """Compute the available journals for the current company """
        for record in self:
            record.available_journal_ids = self.env['account.journal'].search([
                *self.env['account.journal']._check_company_domain(
                    record.company_id),
                ('type', 'in', ('bank', 'cash'))]).ids

    @api.depends('journal_id')
    def _compute_payment_method_line_ids(self):
        """    Compute the available payment method lines based on the journal_id """
        for record in self:
            record.debt_id = record.debt_id.browse(
                self.env.context.get('active_id'))
            payment_type = 'inbound' if self.debt_id.debt_type == 'take' else 'outbound'
            record.payment_method_line_ids = record.journal_id._get_available_payment_method_lines(
                payment_type)
            record.partner_id = record.debt_id.person_id.id if payment_type == 'outbound' \
                else self.env.company.partner_id.id
            record.payback_partner_id = record.debt_id.person_id.id if payment_type == 'inbound' \
                else self.env.company.partner_id.id

    def action_confirm_payment(self):
        """ Creating Payment by confirming the debt """
        self.debt_id = self.debt_id.browse(self.env.context.get('active_id'))
        payment = self.env['account.payment'].create({
            'partner_id': self.debt_id.person_id.id,
            'company_id': self.env.user.company_id.id,
            'amount': self.debt_id.amount,
            'payment_type': 'inbound' if self.debt_id.debt_type == 'borrow' else 'outbound',
            'partner_type': 'customer',
            'journal_id': self.journal_id.id,
            'payment_method_line_id': self.payment_method_line_id.id,
            'partner_bank_id': self.recipient_bank_id.id,
            'ref': self.debt_id.display_name,
        })
        payment.action_post()
        self.debt_id.state = 'lend_borrow'
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'target': 'new',
            'params': {
                'message': _("Successfully Created Payment"),
                'type': 'success',
                'next': {'type': 'ir.actions.act_window_close'},

            }
        }

    def action_confirm_payback(self):
        """ Creating Return Payment by confirming the Payback """
        self._onchange_return_type()
        payment = self.env['account.payment'].create({
            'partner_id': self.debt_id.person_id.id,
            'company_id': self.env.user.company_id.id,
            'amount': self.amount,
            'payment_type': 'inbound' if self.debt_id.debt_type == 'lend' else 'outbound',
            'partner_type': 'customer',
            'journal_id': self.journal_id.id,
            'payment_method_line_id': self.payment_method_line_id.id,
            'partner_bank_id': self.payback_recipient_bank_id.id,
            'ref': f" Payback of {self.debt_id.display_name}",

        })
        payment.action_post()
        self.debt_id.state = 'partial_return' if self.return_type == 'partial' else 'return'
        self.debt_id.returned_or_not = True if self.return_type == 'full' else False
        if not self.debt_id.balance_amount:
            self.debt_id.balance_amount = self.balance_amount if self.return_type == 'partial' else 0
        else:
            self.debt_id.balance_amount -= self.amount
        self.debt_id.partially_returned = True if self.return_type == 'partial' else False
        self.debt_id.returned_date = fields.date.today()
        self.debt_id.returned_amount = self.debt_id.amount - self.debt_id.balance_amount
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'target': 'new',
            'params': {
                'message': _("Successfully Created Return Payment"),
                'type': 'success',
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }

    @api.onchange('return_type', 'amount')
    def _onchange_return_type(self):
        """Amount changes according to the return type"""
        debit_amount = self.debt_id.balance_amount if self.debt_id.partially_returned else self.debt_id.amount
        if self.return_type == 'partial' and self.amount:
            self.balance_amount = debit_amount - self.amount
        else:
            self.amount = debit_amount

    @api.constrains('amount')
    def _check_amount(self):
        """Constraints for the Amount"""
        if self.amount > self.debt_id.amount:
            raise ValidationError('Please Check The Amount..')
