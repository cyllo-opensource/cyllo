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
from math import ceil

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import start_of


class EmployeeSalaryAttachment(models.Model):
    """ Input for Salary Attachments: Handle attachments pertaining to
    salaries."""
    _name = 'employee.salary.attachment'
    _description = 'Employee Salary Attachment'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'description'

    def _get_attachment_domain(self):
        """Get domain to filter records related to specific salary attachments"""
        attached_salary_id = self.env.ref('cyllo_payroll_management.employee_payslip_other_input_attachment_of_salary')
        assigned_salary_id = self.env.ref('cyllo_payroll_management.employee_payslip_other_input_assignment_of_salary')
        child_support_id = self.env.ref('cyllo_payroll_management.employee_payslip_other_input_child_support')
        return [('id', 'in', [attached_salary_id.id, assigned_salary_id.id, child_support_id.id])]

    employee_id = fields.Many2one('hr.employee', required=True, help='Enter the name of employee or select one')
    description = fields.Char(required=True, help='Enter the comments to be added to payslip')
    employee_payslip_other_input_id = fields.Many2one('employee.payslip.other.input', string='Type',
                                                      tracking=True, domain=_get_attachment_domain,
                                                      ondelete='restrict', help='Deduction type', required=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company,
                                 help='Select the company')
    currency_id = fields.Many2one(related='company_id.currency_id', help='Currency of company')
    start_date = fields.Date(help='Enter the starting date',
                             default=lambda self: start_of(fields.Date.today(), 'month'))
    end_date = fields.Date(string='Estimated End date', help='Approximated end date', compute='_compute_end_date')
    attachment = fields.Binary(string='Document', help='Please add supporting document')
    attachment_name = fields.Char(help='This name is shown as attachment name')
    month_amount = fields.Monetary(string='Monthly Amount', required=True, tracking=True,
                                   help='Amount to pay each month')
    total_amount = fields.Monetary(tracking=True, help='Total amount to be paid')
    is_total_amount = fields.Boolean(string='Total Amount Available', help='Total payment is enabled',
                                     compute='_compute_is_total_amount')
    balance = fields.Monetary(compute='_compute_balance', store=True, help='Balance amount to be paid')
    paid_amount = fields.Monetary(readonly=True, tracking=True, help='Total paid amount')
    active_amount = fields.Monetary(store=True, compute='_compute_active_amount', help='Active amount to be paid')
    state = fields.Selection([('running', 'Running'), ('completed', 'Completed'), ('cancelled', 'Cancelled')],
                             string='Status', default='running', help='status of salary attachment')

    @api.depends('month_amount', 'total_amount')
    def _compute_end_date(self):
        """ Compute the 'end_date' based on 'month_amount' and 'total_amount' fields"""
        for record in self:
            if record.month_amount:
                if record.month_amount >= record.total_amount:
                    record.end_date = record.start_date + relativedelta(months=1)
                else:
                    months_required = ceil(record.total_amount / record.month_amount)
                    record.end_date = record.start_date + relativedelta(months=months_required)
            else:
                record.end_date = False

    @api.depends('employee_payslip_other_input_id')
    def _compute_is_total_amount(self):
        """ Compute the 'is_total_amount' based on 'employee_payslip_other_input_id' field"""
        for record in self:
            record.is_total_amount = record.employee_payslip_other_input_id != record.env.ref(
                'cyllo_payroll_management.employee_payslip_other_input_child_support')

    @api.depends('month_amount', 'total_amount', 'paid_amount')
    def _compute_balance(self):
        """ Compute method of 'balance' based on 'month_amount', 'total_amount', 'paid_amount' fields"""
        for record in self:
            if record.is_total_amount:
                record.balance = max(0, (record.total_amount - record.paid_amount))
            else:
                record.balance = record.month_amount

    @api.depends('month_amount', 'paid_amount', 'balance')
    def _compute_active_amount(self):
        """ Compute method of 'active_amount' based on 'month_amount', 'paid_amount', 'balance' fields"""
        for record in self:
            record.active_amount = min(record.month_amount, record.balance)

    @api.constrains('month_amount', 'total_amount', 'start_date', 'end_date')
    def _check_month_amount(self):
        """ To check the amount """
        if self.month_amount <= 0:
            raise ValidationError(_("Monthly amount should be positive"))
        if self.is_total_amount and self.total_amount < self.month_amount or self.total_amount < 0:
            raise ValidationError(_("Total amount must be strictly positive and greater than or equal to the monthly "
                                    "amount"))

    @api.constrains('start_date', 'end_date')
    def _check_start_date(self):
        """ To check the dates"""
        if self.end_date and self.start_date >= self.end_date:
            raise ValidationError(_("End date should be after the start date"))

    def unlink(self):
        """ To prevent the deleting of running salary attachment"""
        if any(record.state == 'running' for record in self):
            raise UserError(_('You cannot delete a running salary attachment!'))
        return super(EmployeeSalaryAttachment, self).unlink()

    def action_done(self):
        """To move the record in completed state"""
        self.write({'state': 'completed'})

    def action_cancel(self):
        """To move the record in cancelled state"""
        self.write({'state': 'cancelled'})

    def action_open(self):
        """To move the record in running state"""
        self.write({'state': 'running'})

    def record_paid_amount(self, paid_amount):
        """ This method record the payment of salary attachment """
        if self.balance <= paid_amount:
            remaining_amount = self.balance
            self.paid_amount = self.paid_amount + self.balance
            self.action_done()
            carried_to_next = paid_amount - remaining_amount
            return carried_to_next
        else:
            self.paid_amount = self.paid_amount + paid_amount