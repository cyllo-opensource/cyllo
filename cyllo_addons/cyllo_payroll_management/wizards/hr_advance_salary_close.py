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
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class HrAdvanceSalaryCloseWizard(models.TransientModel):
    _name = 'hr.advance.salary.close.wizard'
    _description = 'Advance Salary Close Wizard'

    advance_id = fields.Many2one('hr.advance.salary', string="Advance Request",
                                 required=True)
    advance_remaining_amount = fields.Float(
        related='advance_id.remaining_amount', string="Current Balance")

    close_type = fields.Selection([
        ('full', 'Fully Closing'),
        ('partial', 'Partial Closing')
    ], string="Close Type", default='partial', required=True)

    closing_amount = fields.Float(string="Closing Amount")
    remaining_after_closing = fields.Float(
        string="Remaining Balance",
        compute="_compute_remaining_after_closing"
    )

    balance_action = fields.Selection([
        ('write_off', 'Write Off Balance'),
        ('schedule', 'Reschedule in Future Payslips')
    ], string="Balance Action",
        help="What to do with the remaining amount after partial payment")

    deduction_amount = fields.Float(
        string="Fixed Deduction Amount",
        help="Fixed amount to deduct from each payslip"
    )

    deduction_percentage = fields.Float(
        string="Deduction Percentage",
        help="Percentage to deduct from each payslip (0-100)"
    )
    is_percentage = fields.Boolean(
        string="Is Percentage Based",
        compute="_compute_is_percentage",
        store=True
    )
    loss_account_id = fields.Many2one('account.account', string="Loss Account")
    account_id = fields.Many2one('account.account', string="Payment Account")

    reason = fields.Text(string="Reason")

    @api.depends('advance_id', 'advance_id.deduction_type')
    def _compute_is_percentage(self):
        """Determine if deduction is percentage-based from the advance request"""
        for rec in self:
            rec.is_percentage = (
                    rec.advance_id and
                    rec.advance_id.deduction_type == 'percentage'
            )

    @api.depends('advance_remaining_amount', 'closing_amount')
    def _compute_remaining_after_closing(self):
        for rec in self:
            rec.remaining_after_closing = max(0,
                                              rec.advance_remaining_amount - rec.closing_amount)



    def action_close(self):
        self.ensure_one()
        advance = self.advance_id
        company = advance.employee_id.company_id or self.env.company
        credit_account = company.advance_salary_account_id

        if not credit_account:
            raise UserError(
                _("Please configure 'Advance Salary Account' in Payroll Settings."))

        # Snapshot values before any changes
        current_opt_remaining = advance.remaining_amount
        # Use wizard's computed remaining if available/relevant, or recompute locally
        # Safe approach:
        amount_to_pay = 0.0
        remaining_to_handle = 0.0

        if self.close_type == 'full':
            amount_to_pay = current_opt_remaining
            remaining_to_handle = 0.0
        else:  # Partial
            amount_to_pay = self.closing_amount
            if amount_to_pay > current_opt_remaining:
                raise UserError(
                    _("Closing amount cannot be greater than the remaining advance amount."))
            remaining_to_handle = max(0, current_opt_remaining - amount_to_pay)

        # 1. Create Journal Entry for Payment
        if amount_to_pay > 0:
            if not self.account_id:
                raise UserError(_("Please select a Payment Account."))

            partner = advance.employee_id.work_contact_id or advance.employee_id.user_id.partner_id
            if not partner:
                partner = self.env['res.partner'].search(
                    [('name', '=', advance.employee_id.name)], limit=1)

            payment_move = self._create_journal_entry(
                advance, partner, self.account_id, credit_account,
                amount_to_pay,
                ref=f"Repayment of {advance.name}"
            )
            # Link payment move to advance to reduce remaining balance
            advance.write({'payment_move_ids': [(4, payment_move.id)]})

        # 2. Handle Remaining Balance
        if self.close_type == 'full':
            # Full close always closes
            advance.line_ids.filtered(lambda l: l.state == 'planned').write(
                {'is_canceled': True})
            advance.write({'state': 'closed'})

        elif self.close_type == 'partial':

            if remaining_to_handle > 0.01:
                if self.balance_action == 'write_off':
                    if not self.loss_account_id:
                        raise UserError(
                            _("Please select a Loss Account for write-off."))

                    partner = advance.employee_id.work_contact_id

                    write_off_move = self._create_journal_entry(
                        advance, partner, self.loss_account_id, credit_account,
                        remaining_to_handle,
                        ref=f"Write-off balance of {advance.name}"
                    )
                    advance.write(
                        {'payment_move_ids': [(4, write_off_move.id)]})

                    # Close the advance as it is written off
                    advance.line_ids.filtered(
                        lambda l: l.state == 'planned').write(
                        {'is_canceled': True})
                    advance.write({'state': 'closed'})

                elif self.balance_action == 'schedule':
                    if self.is_percentage:
                        if self.deduction_percentage>0:
                            self.advance_id.write({
                                'deduction_percentage':self.deduction_percentage
                            })
                        else:
                            self.advance_id.write({
                                'deduction_percentage': self.advance_id.deduction_percentage
                            })
                    else:
                        if self.deduction_amount>0:
                            self.advance_id.write(
                                {'deduction_amount': self.deduction_amount})
                        else:
                            self.advance_id.write(
                                {'deduction_amount': self.advance_id.deduction_amount})

                    # Reschedule uses the live remaining amount (which now reflects the payment)
                    advance.reschedule_balance()

            # If nothing remaining to handle (paid in full manually via partial option), close it
            elif remaining_to_handle <= 0.01:
                advance.line_ids.filtered(lambda l: l.state == 'planned').write(
                    {'is_canceled': True})
                advance.write({'state': 'closed'})

        return {'type': 'ir.actions.act_window_close'}

    def _create_journal_entry(self, advance, partner, debit_account,
                              credit_account, amount, ref):
        move_vals = {
            'move_type': 'entry',
            'date': fields.Date.today(),
            'ref': ref,
            'line_ids': [
                (0, 0, {
                    'name': ref,
                    'partner_id': partner.id if partner else False,
                    'account_id': debit_account.id,
                    'debit': amount,
                    'credit': 0.0,
                }),
                (0, 0, {
                    'name': ref,
                    'partner_id': partner.id if partner else False,
                    'account_id': credit_account.id,
                    'debit': 0.0,
                    'credit': amount,
                }),
            ],
        }
        move = self.env['account.move'].sudo().create(move_vals)
        move.action_post()
        return move
