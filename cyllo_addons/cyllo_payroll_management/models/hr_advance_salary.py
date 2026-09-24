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
from dateutil.relativedelta import relativedelta


class HrAdvanceSalary(models.Model):
    _name = 'hr.advance.salary'
    _description = 'Advance Salary'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'

    name = fields.Char(
        string="Reference",
        default="New",
        copy=False,
        readonly=True
    )

    company_id = fields.Many2one(
        'res.company',
        string="Company",
        required=True,
        default=lambda self: self.env.company,
        index=True
    )

    employee_id = fields.Many2one(
        'hr.employee',
        string="Employee",
        required=True,
        tracking=True,
        default=lambda self: self.env['hr.employee'].sudo().search(
            [('user_id', '=', self.env.uid)], limit=1
        )
    )

    request_date = fields.Date(
        string="Request Date",
        default=fields.Date.today
    )

    amount = fields.Float(
        string="Requested Amount",
        required=True,
        tracking=True
    )

    deduction_type = fields.Selection([
        ('fixed', 'Fixed Amount'),
        ('percentage', 'Percentage of Monthly Wage')
    ], string="Deduction Type", default='fixed', required=True,
        help="Choose how to calculate monthly deductions")

    deduction_amount = fields.Float(
        string="Fixed Deduction Amount",
        help="Fixed amount to deduct from each payslip"
    )

    deduction_percentage = fields.Float(
        string="Deduction Percentage",
        help="Percentage to deduct from each payslip (0-100)"
    )

    monthly_deduction_amount = fields.Float(
        string="Monthly Deduction Amount",
        compute="_compute_monthly_deduction_amount",
        help="Calculated monthly deduction amount based on the deduction type and percentage/fixed amount."
    )

    approval_date = fields.Date(
        string="Approval Date",
        readonly=True,
        tracking=True
    )

    reason = fields.Text(string="Reason")

    # Deduction tracking fields
    deducted_amount = fields.Float(
        string="Deducted Amount",
        compute="_compute_deducted_amount",
        store=True,
        help="Total amount already deducted from payslips"
    )
    remaining_amount = fields.Float(
        string="Remaining Amount",
        compute="_compute_remaining_amount",
        store=True,
        help="Amount still to be deducted from future payslips"
    )
    payslip_input_ids = fields.One2many(
        'employee.payslip.input',
        'advance_salary_id',
        string="Payslip Deductions",
        help="Payslip input lines that deducted from this advance"
    )

    bill_id = fields.Many2one(
        'account.move',
        string="Vendor Bill",
        readonly=True,
        tracking=True,
        help="Vendor bill created for this advance salary"
    )

    currency_id = fields.Many2one(
        'res.currency',
        string="Currency",
        related='company_id.currency_id',
        readonly=True
    )
    payment_move_ids = fields.Many2many(
        'account.move',
        string="Payment Entries",
        readonly=True,
        help="Journal entries created for manual repayments or closing"
    )

    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('paid', 'Paid'),
        ('closed', 'Closed')
    ], default='draft', tracking=True)

    @api.depends('deduction_type', 'deduction_amount', 'deduction_percentage',
                 'employee_id')
    def _compute_monthly_deduction_amount(self):
        """Compute the monthly deduction amount based on the deduction type"""
        for rec in self:
            rec.monthly_deduction_amount = rec._get_monthly_deduction_amount()

    @api.onchange('deduction_type')
    def _onchange_deduction_type(self):
        """Clear the opposite field when switching deduction type"""
        if self.deduction_type == 'fixed':
            self.deduction_percentage = 0.0
        elif self.deduction_type == 'percentage':
            self.deduction_amount = 0.0

    @api.onchange('deduction_percentage')
    def _onchange_deduction_percentage(self):
        """Validate percentage is within valid range (0-100)"""
        if self.deduction_percentage < 0:
            self.deduction_percentage = 0.0
        elif self.deduction_percentage > 100:
            self.deduction_percentage = 100.0

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        """Warn if employee has no active contract"""
        if not self.employee_id:
            return

        if not self._origin.id:
            return

        contract = self.env['hr.contract'].sudo().search([
            ('employee_id', '=', self.employee_id.id),
            ('state', '=', 'open')
        ], limit=1)

        if not contract:
            return {
                'warning': {
                    'title': _('No Active Contract'),
                    'message': _(
                        'The selected employee does not have an active contract. '
                        'Monthly deduction amount may not be calculated correctly.'
                    )
                }
            }

    def _get_monthly_deduction_amount(self, contract=None):
        """Helper to calculate monthly deduction amount"""
        self.ensure_one()
        if self.deduction_type == 'fixed':
            return self.deduction_amount

        if not contract:
            contract = self.env['hr.contract'].sudo().search([
                ('employee_id', '=', self.employee_id.id),
                ('state', '=', 'open')
            ], limit=1)

        if not contract:
            return 0.0

        if self.deduction_type == 'percentage':
            # Use contract.wage which is the monthly wage
            return (contract.wage or 0.0) * (self.deduction_percentage / 100.0)

        return 0.0

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code(
                'advance.salary.request'
            ) or 'New'
        return super().create(vals)

    def action_submit(self):
        for rec in self:
            rec.state = 'submitted'

    def action_approve(self):
        for rec in self:
            # Safety: if user forgot to set deduction
            if rec.deduction_type == 'fixed' and rec.deduction_amount <= 0:
                rec.deduction_amount = rec.amount
            elif rec.deduction_type == 'percentage' and rec.deduction_percentage <= 0:
                rec.deduction_percentage = 100.0
            rec.approval_date = fields.Date.today()
            rec.state = 'approved'

            # Generate schedule
            rec._generate_deduction_schedule()

    def action_reject(self):
        for rec in self:
            rec.state = 'rejected'

    def action_create_bill(self):
        """Create a Vendor Bill for the advance salary amount"""
        for rec in self:
            if rec.bill_id:
                continue

            # Find the partner for the employee
            partner = rec.employee_id.work_contact_id or rec.employee_id.user_id.partner_id
            if not partner:
                partner = self.env['res.partner'].search(
                    [('name', '=', rec.employee_id.name)], limit=1)

            if not partner:
                raise UserError(
                    _("Cannot find a related partner for this employee. Please set a work contact or user."))

            # Retrieve configuration
            company = rec.employee_id.company_id or self.env.user.company_id
            debit_account = company.advance_salary_account_id
            credit_account = company.advance_salary_payment_account_id

            if not debit_account or not credit_account:
                raise UserError(
                    _("Please configure both 'Advance Salary Account' and 'Payment Account' in Payroll Settings."))

            # Create Journal Entry
            move_vals = {
                'move_type': 'entry',
                'date': fields.Date.today(),
                'ref': rec.name,
                'line_ids': [
                    (0, 0, {
                        'name': f"Advance Salary for {rec.employee_id.name} ({rec.name})",
                        'partner_id': partner.id,
                        'account_id': debit_account.id,
                        'debit': rec.amount,
                        'credit': 0.0,
                    }),
                    (0, 0, {
                        'name': f"Advance Salary for {rec.employee_id.name} ({rec.name})",
                        'partner_id': partner.id,
                        'account_id': credit_account.id,
                        'debit': 0.0,
                        'credit': rec.amount,
                    }),
                ],
            }
            bill = self.env['account.move'].sudo().create(move_vals)
            bill.action_post()  # Post the entry as it's a journal entry
            rec.bill_id = bill.id
            rec.state = 'paid'
            return {
                'name': 'Vendor Bill',
                'view_mode': 'form',
                'res_model': 'account.move',
                'res_id': bill.id,
                'type': 'ir.actions.act_window',
            }

    def get_bill_action(self):
        """Action for the stat button to view the bill"""
        self.ensure_one()
        return {
            'name': 'Vendor Bill',
            'view_mode': 'form',
            'res_model': 'account.move',
            'res_id': self.bill_id.id,
            'type': 'ir.actions.act_window',
        }

    def action_paid(self):
        for rec in self:
            rec.state = 'paid'

    @api.depends('payslip_input_ids', 'payslip_input_ids.amount',
                 'payment_move_ids', 'payment_move_ids.amount_total')
    def _compute_deducted_amount(self):
        """Calculate total amount deducted from payslips and manual payments"""
        for rec in self:
            # Sum absolute values since amounts are stored as negative
            payslip_deductions = abs(
                sum(rec.payslip_input_ids.mapped('amount')))
            # Add manual payments (assuming credit entries to advance account in payment moves)
            manual_payments = sum(rec.payment_move_ids.mapped('amount_total'))
            rec.deducted_amount = payslip_deductions + manual_payments

    @api.depends('amount', 'deducted_amount')
    def _compute_remaining_amount(self):
        """Calculate remaining amount to be deducted"""
        for rec in self:
            rec.remaining_amount = rec.amount - rec.deducted_amount

    @api.model
    def get_active_advances_for_employee(self, employee_id, date=None):
        """Get approved advances with remaining balance for an employee

        Args:
            employee_id: ID of the employee
            date: Reference date (default: today)

        Returns:
            recordset of hr.advance.salary with remaining balance
        """
        domain = [
            ('employee_id', '=', employee_id),
            ('state', '=', 'paid'),
            ('remaining_amount', '>', 0)
        ]
        return self.search(domain, order='request_date')

    @api.constrains('amount', 'deduction_type', 'deduction_amount')
    def _check_monthly_deduction_less_than_amount(self):
        for rec in self:
            if rec.deduction_type == 'fixed':
                if rec.deduction_amount > rec.amount:
                    raise UserError(_(
                        "Monthly deduction amount must be less than the requested advance amount."
                    ))

    line_ids = fields.One2many(
        'hr.advance.salary.line',
        'advance_id',
        string="Deduction Schedule"
    )

    def _generate_deduction_schedule(self):
        """Generate predicted deduction lines"""
        self.ensure_one()
        self.line_ids.unlink()

        remaining = self.amount
        monthly = self.monthly_deduction_amount
        if monthly <= 0:
            return  # Or raise error?

        current_date = (self.approval_date or fields.Date.today()).replace(
            day=1)
        # Start deduction from next month? Usually advance is deducted from next month or current?
        # Let's assume next month for consistency with reschedule_balance, 
        # or keeping current month if that was the intent. 
        # The previous code started from approval_date. Let's stick to that but use relativedelta.

        lines = []
        while remaining > 0.01:
            deduction = min(monthly, remaining)
            lines.append((0, 0, {
                'date': current_date,
                'amount': deduction,
                'state': 'planned'
            }))
            remaining -= deduction
            current_date += relativedelta(months=1)

        self.write({'line_ids': lines})

    def reschedule_balance(self):
        """Reschedule the remaining balance"""
        self.ensure_one()
        # Remove only planned lines
        self.line_ids.filtered(lambda l: l.state == 'planned').unlink()

        # Recalculate remaining amount (will be updated by _compute_remaining_amount)
        # But we need it now for scheduling
        remaining = self.amount - self.deducted_amount

        if remaining <= 0:
            return

        monthly = self.monthly_deduction_amount
        if monthly <= 0:
            # Prevent infinite loop if monthly is 0, defaults to full remaining
            monthly = remaining

        # Start from next month relative to today
        current_date = (fields.Date.today() + relativedelta(months=1)).replace(
            day=1)

        lines = []
        while remaining > 0.01:  # Float epsilon
            deduction = min(monthly, remaining)
            lines.append((0, 0, {
                'date': current_date,
                'amount': deduction,
                'state': 'planned'
            }))
            remaining -= deduction
            current_date += relativedelta(months=1)

        self.write({'line_ids': lines})


class HrAdvanceSalaryLine(models.Model):
    _name = 'hr.advance.salary.line'
    _description = 'Advance Salary Deduction Line'
    _order = 'date asc'

    advance_id = fields.Many2one('hr.advance.salary', string="Advance Request",
                                 ondelete='cascade')
    date = fields.Date(string="Deduction Month")
    amount = fields.Float(string="Amount")
    payslip_id = fields.Many2one('employee.payslip', string="Payslip",
                                 readonly=True)
    currency_id = fields.Many2one(
        'res.currency',
        string="Currency",
        related='advance_id.currency_id',
        readonly=True
    )
    state = fields.Selection([
        ('planned', 'Planned'),
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('canceled', 'Canceled')
    ], string="Status", compute="_compute_state", store=True)
    is_canceled = fields.Boolean(string="Is Canceled", default=False)

    @api.depends('payslip_id', 'payslip_id.state', 'is_canceled')
    def _compute_state(self):
        for rec in self:
            if rec.is_canceled:
                rec.state = 'canceled'
            elif not rec.payslip_id:
                rec.state = 'planned'
            else:
                rec.state = 'paid'
