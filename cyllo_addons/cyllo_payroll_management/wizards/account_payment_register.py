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
import logging
from odoo import api, models

_logger = logging.getLogger(__name__)


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    @api.depends('can_edit_wizard', 'journal_id')
    def _compute_available_partner_bank_ids(self):
        """Override to handle bank account availability for batch payslips with batch_move_line=True"""
        payroll_context = self._context.get('payroll_register_payment')

        # Only apply custom logic for batch payslips with batch_move_line=True
        if type(payroll_context) is int:
            batch = self.env['employee.payslip.batch'].browse(payroll_context).exists()
            if batch and batch.batch_move_line:
                for wizard in self:
                    if wizard.payment_type == 'outbound':
                        employees = batch.employee_payslip_ids.mapped('employee_id')
                        employee_banks = employees.mapped('bank_account_id').filtered(lambda b: b)
                        wizard.available_partner_bank_ids = employee_banks
                    else:
                        super(AccountPaymentRegister, wizard)._compute_available_partner_bank_ids()
                return
        
        super()._compute_available_partner_bank_ids()

    def action_create_payments(self):
        res = super().action_create_payments()

        # Check if this is from batch payslip with batch_move_line enabled
        batch_id = self._context.get('payroll_register_payment')
        if isinstance(batch_id, int) and not isinstance(batch_id, bool) and batch_id:
            # Try to get batch first
            batch = self.env['employee.payslip.batch'].browse(batch_id).exists()
            if batch and batch.batch_move_line:
                if all(line.amount_residual == 0 for line in self.line_ids):
                    batch.write({'state': 'paid'})
                    batch.employee_payslip_ids.action_paid()
            elif batch and not batch.batch_move_line:
                _logger.info('batch without batch_move_line - should not reach here')
            else:
                payslip = self.env['employee.payslip'].browse(batch_id).exists()
                if payslip and not payslip.is_batch_payslip:
                    if all(line.amount_residual == 0 for line in self.line_ids):
                        payslip.action_paid()
        elif batch_id is True:
            processed_payslips = self.env['employee.payslip']
            for line in self.line_ids:
                if line.move_id:
                    payslip = self.env['employee.payslip'].search([('account_move_id', '=', line.move_id.id)], limit=1)
                    if payslip:
                        processed_payslips |= payslip
            
            payslips_to_mark_paid = self.env['employee.payslip']
            for payslip in processed_payslips:
                payslip_lines = self.line_ids.filtered(lambda l: l.move_id == payslip.account_move_id)
                if payslip_lines and all(line.amount_residual == 0 for line in payslip_lines):
                    payslips_to_mark_paid |= payslip
            
            if payslips_to_mark_paid:
                payslips_to_mark_paid.action_paid()
                
                batch = payslips_to_mark_paid[0].employee_payslip_batch_id if payslips_to_mark_paid else False
                if batch:
                    all_batch_payslips = batch.employee_payslip_ids
                    if all(p.state == 'paid' for p in all_batch_payslips):
                        batch.write({'state': 'paid'})
        
        return res