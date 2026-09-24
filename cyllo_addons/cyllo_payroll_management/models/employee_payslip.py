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
import babel
import calendar
import math
from datetime import datetime, time, timedelta
from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models, tools
from odoo.exceptions import UserError, ValidationError
from odoo.tools import date_utils
from odoo.addons import decimal_precision as decimal
from collections import defaultdict


class EmployeePayslip(models.Model):
    """By using this class we can create and generate the salary slip of the
    employee"""
    _name = 'employee.payslip'
    _description = 'Employee Payslip'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'payslip_name'

    reference = fields.Char(readonly=True, copy=False, default='New',
                            string='Sequence', help='Reference for payslip')
    employee_id = fields.Many2one('hr.employee', required=True,
                                  help='To choose the employee')
    image_1920 = fields.Binary(related='employee_id.image_1920')
    start_date = fields.Date(string='Date From', required=True,
                             help="Start date of payslip",
                             default=lambda self: fields.Date.to_string(
                                 fields.Date.today().replace(day=1)))
    to_date = fields.Date(string='Date To', required=True, readonly=False,
                          help="End date of payslip", store=True,
                          compute='_compute_to_date', precompute=True)
    company_id = fields.Many2one('res.company', required=True,
                                 default=lambda self: self.env.company)
    contract_id = fields.Many2one('hr.contract',
                                  domain="[('employee_id', '=', employee_id), ('state', 'in', ['training', 'open', 'close'])]",
                                  help='Contract for the selected employee',
                                  required=True)
    structure_id = fields.Many2one('employee.salary.structure',
                                   string='Salary Structure',
                                   help="Establish the rules for this payslip based on the selected contract",
                                   required=True)
    journal_id = fields.Many2one(related='structure_id.journal_id',
                                 readonly=False,
                                 help='Journal related to the structure')
    batch = fields.Integer(help='To get the id of the batch')
    state = fields.Selection(
        [('draft', 'Draft'), ('waiting', 'Waiting'), ('done', 'Done'),
         ('paid', 'Paid'), ('cancel', 'Rejected')], default='draft')
    payslip_name = fields.Char(compute='_compute_payslip_name', store=True,
                               help='Name of payslip')
    attendance_count = fields.Integer(compute='_compute_attendance_count',
                                      store=True,
                                      help='Total attendance count for the payslip employee')
    entry_count = fields.Integer(string='Work Entry Count',
                                 compute='_compute_work_entry_ids', store=True,
                                 help='Count of work entries for payslip employee')
    employee_worked_days_ids = fields.One2many('employee.worked.days',
                                               'employee_payslip_id',
                                               # compute='_compute_employee_id',
                                               store=True, copy=True,
                                               help='Work days of payslip employee')
    date_warning_message = fields.Char(string='Warning Message',
                                       compute='_compute_date_warning_message',
                                       help='The warning messages for the payslip date violates the salary '
                                            'schedule pay', store=True,
                                       readonly=False)
    credit_note = fields.Boolean(readonly=True,
                                 help="Indicates this payslip has a refund of another")
    account_move_id = fields.Many2one('account.move', string='Accounting Entry',
                                      ondelete='restrict',
                                      help='The account move of payslip where the journal entry posted',
                                      readonly=True,
                                      copy=False)
    is_batch_payslip = fields.Boolean(string='Batch Payslip',
                                      help='To check whether the payslip is generated form the batch or not ')
    batch_payslip_name = fields.Char(help='To get the batch payslip name')
    salary_attachment_ids = fields.Many2many('employee.salary.attachment',
                                             string='Salary Attachments',
                                             help='The attachments related to the salary information for this record.')
    work_entry_ids = fields.Many2many("hr.work.entry",
                                      compute="_compute_work_entry_ids")
    total_worked_hours = fields.Float(
        help='The total hours worked by the employee',
        compute='_compute_total_worked_hours')
    total_amount = fields.Float(help='Total amount to be paid',
                                compute='_compute_total_amount')
    employee_payslip_batch_id = fields.Many2one('employee.payslip.batch',
                                                string='Payslip Batches',
                                                help='Relation to the batch',
                                                copy=False)
    employee_payslip_line_ids = fields.One2many('employee.payslip.line',
                                                'employee_payslip_id',
                                                copy=True,
                                                help='The payslip rules associated with this payslip')
    employee_payslip_input_ids = fields.One2many('employee.payslip.input',
                                                 'payslip_id',
                                                 string='Payslip Inputs',
                                                 copy=True,
                                                 help='The payslip inputs associated with this payslip.')
    gratuity_settlement_ids = fields.Many2many('gratuity.settlement',
                                               compute="_compute_gratuity_settlement_ids")
    gratuity_settlement_id = fields.Many2one('gratuity.settlement')
    parent_id = fields.Many2one(comodel_name='employee.payslip')
    refund_count = fields.Integer(compute="_compute_refund_count",
                                  string="Refund Count", readonly=True)
    expense_sheet_ids = fields.Many2many(
        'hr.expense.sheet',
        string='Expense Sheets',
        help='Expense sheets included in this payslip'
    )
    expense_sheet_count = fields.Integer(
        string='Expense Count',
        compute='_compute_expense_sheet_count',
        help='Number of expense sheets linked to this payslip'
    )
    commission_report_ids = fields.Many2many(
        'commission.report',
        string='Commissions',
        help='Commissions included in this payslip'
    )
    commission_report_count = fields.Integer(
        string='Commission Count',
        compute='_compute_commission_report_count',
        help='Number of commission reports linked to this payslip'
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='company_id.currency_id',
        readonly=True,
    )

    net_salary_amount = fields.Monetary(
        string='Net Salary',
        currency_field='currency_id',
        compute='_compute_salary_summary',
        store=True,
    )

    @api.depends('start_date')
    def _compute_to_date(self):
        """ Compute method to calculate the end date of the payslip"""
        for record in self:
            if record.start_date:
                end_of_month = calendar.monthrange(record.start_date.year,
                                                   record.start_date.month)[1]
                record.to_date = record.start_date.replace(day=end_of_month)
            else:
                record.to_date = date_utils.end_of(fields.Date.today(), 'month')

    @api.depends('employee_id', 'start_date')
    def _compute_payslip_name(self):
        """To compute the name for the payslip"""
        for payslip in self.filtered(lambda x: x.employee_id and x.start_date):
            employee_name = payslip.employee_id.name
            month_year = fields.Date.from_string(payslip.start_date).strftime(
                '%B %Y')
            payslip.payslip_name = f'Pay Slip - {employee_name} - {month_year}'

    @api.depends('employee_id')
    def _compute_attendance_count(self):
        """To compute the count of the attendance of the particular employee"""
        for attendance in self:
            attendance.attendance_count = self.env[
                'hr.attendance'].sudo().search_count(
                [('employee_id.id', '=', attendance.employee_id.id)])

    def _compute_refund_count(self):
        """To compute the count of the refund of the particular payslip"""
        for record in self:
            record.refund_count = self.search_count(
                [('parent_id', '=', record.id)])

    @api.depends('expense_sheet_ids')
    def _compute_expense_sheet_count(self):
        """Compute the count of expense sheets linked to this payslip"""
        for record in self:
            record.expense_sheet_count = len(record.expense_sheet_ids)

    @api.depends('commission_report_ids')
    def _compute_commission_report_count(self):
        """Compute the count of commission reports linked to this payslip"""
        for record in self:
            record.commission_report_count = len(record.commission_report_ids)

    @api.depends('employee_payslip_line_ids', 'employee_payslip_line_ids.total',
                 'employee_payslip_line_ids.category_id')
    def _compute_salary_summary(self):
        """Compute salary summary total (Net)."""
        for payslip in self:
            net = 0.0
            for line in payslip.employee_payslip_line_ids:
                code = (line.category_id.code or '').upper()
                if code == 'NET':
                    net += line.total
            payslip.net_salary_amount = net

    def action_view_expense_sheets(self):
        """To view corresponding expense sheets linked to the payslip"""
        return {
            'name': 'Expense Sheets',
            'view_mode': 'tree,form',
            'res_model': 'hr.expense.sheet',
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', self.expense_sheet_ids.ids)],
        }

    def action_view_commission_reports(self):
        """To view corresponding commission reports linked to the payslip"""
        return {
            'name': 'Commissions',
            'view_mode': 'tree,form',
            'res_model': 'commission.report',
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', self.commission_report_ids.ids)],
        }

    @api.depends('employee_id', 'start_date', 'to_date', 'contract_id',
                 'contract_id.work_entry_source')
    def _compute_work_entry_ids(self):
        for rec in self:
            if rec.employee_id and rec.start_date and rec.to_date and rec.contract_id:
                work_entries = self.env['hr.work.entry'].sudo().search(
                    [('employee_id', '=', rec.employee_id.id),
                     ('date_start', '>=', rec.start_date),
                     ('date_stop', '<=', rec.to_date),
                     ('state', '!=', 'conflict'),
                     ('contract_id', '=', rec.contract_id.id)])
                filtered_entries = work_entries.filtered(
                    lambda
                        w: w.work_entry_source == rec.contract_id.work_entry_source)
                rec.work_entry_ids = filtered_entries
                rec.entry_count = len(filtered_entries)
            else:
                rec.work_entry_ids = False
                rec.entry_count = 0

    @api.depends('start_date', 'to_date', 'contract_id', 'structure_id')
    def _compute_date_warning_message(self):
        """Compute method to calculate the warning message based on contract dates and structure"""
        for record in self:
            warning = []
            # Check if the chosen duration corresponds with the contract's validity
            if record.contract_id:
                if ((
                        record.start_date and record.contract_id.date_start > record.start_date) or
                        (
                                record.contract_id.date_end and record.contract_id.date_end < record.to_date)):
                    warning.append(
                        _("The duration chosen does not correspond with the duration of the contract's validity."))
            # Check if the payslip's duration is accurate based on the structure type
            if record.structure_id.schedule_pay or record.contract_id.default_schedule_pay:
                if record.start_date and record.start_date + record.get_date_from_schedule_pay() != record.to_date:
                    warning.append(
                        _("Depending on the type of structure, the payslip's duration is not accurate."))

            # Check if the to_date exceeds the end of the current month
            if record.to_date:
                end_of_month = date_utils.end_of(fields.Date.today(), 'month')
                if record.to_date > end_of_month:
                    warning.append(
                        _("No work entries might be produced during the time frame for %s - %s.") % (
                            fields.Date.today().replace(day=1,
                                                        month=fields.Date.today().month + 1),
                            record.to_date))

            # Set the warning message
            if warning:
                warning = [_("This payslip might not be accurate:")] + warning
                record.date_warning_message = '\n'.join(warning)
            else:
                record.date_warning_message = False

    @api.depends('employee_worked_days_ids.hour')
    def _compute_total_worked_hours(self):
        """Compute method to calculate the total worked hours of the employee in the specified time interval"""
        for record in self:
            record.total_worked_hours = sum(
                line.hour for line in record.employee_worked_days_ids)

    @api.depends('employee_worked_days_ids.amount')
    def _compute_total_amount(self):
        """Compute method to calculate the total amount to be paid based on employee work entries"""
        for amount in self:
            amount.total_amount = sum(
                line.amount for line in amount.employee_worked_days_ids)

    @api.depends('employee_id', 'contract_id')
    def _compute_gratuity_settlement_ids(self):
        """This method search for gratuity settlements applicable for selected
        employee"""
        for rec in self:
            domain = [('employee_id', '=', rec.employee_id.id),
                      ('state', '=', 'confirm')]
            if rec.contract_id.date_end and rec.to_date and rec.contract_id.date_end.month == rec.to_date.month:
                domain.append(('contract_type', '=', 'limited'))
            elif not rec.contract_id.date_end:
                domain.append(('contract_type', '=', 'open'))
            gratuity = self.env['gratuity.settlement'].search(domain,
                                                              order='create_date desc')
            rec.gratuity_settlement_ids = gratuity.ids if gratuity else False

    @api.depends('employee_payslip_input_ids', 'credit_note')
    def _compute_is_attachment_paid(self):
        """Compute method to check if attachment is paid"""
        for payslip in self.filtered(lambda x: x.credit_note):
            for record in payslip.employee_payslip_input_ids.filtered(
                    lambda r: r.is_attachment):
                attachment = payslip.salary_attachment_ids.sudo().search([
                    ('employee_payslip_other_input_id', '=', record.type_id.id),
                    ('state', '=', 'running')])
                amount = record.amount
                for rec in attachment:
                    amount = rec.record_paid_amount(amount)
                    if amount is None:
                        break

    @api.onchange('employee_id', 'start_date', 'to_date', 'contract_id')
    def _onchange_employee_id(self):
        """Update contract and worked days when employee, dates, or contract change"""
        if not self.employee_id or not self.start_date or not self.to_date:
            return
        employee_id = self.employee_id
        start_date = self.start_date
        to_date = self.to_date

        # Reset contract and worked days if employee or dates are not set
        if not self.env.context.get('contract') or not self.contract_id:
            contract_ids = self.get_employee_contract(employee_id, start_date,
                                                      to_date)
            if not contract_ids:
                self.contract_id = False
                self.employee_worked_days_ids = False
                return
            self.contract_id = self.env['hr.contract'].sudo().browse(
                contract_ids[0])

        # Update structure and worked days based on the contract
        self.structure_id = self.contract_id.employee_salary_structure_id or self.structure_id
        employee_contracts = self.env['hr.contract'].sudo().browse(
            [self.contract_id.id])
        worked_days_line_ids = self.get_worked_day_lines(employee_id,
                                                         start_date, to_date,
                                                         employee_contracts[0])
        self.employee_worked_days_ids = [fields.Command.clear()]
        self.employee_worked_days_ids = [fields.Command.create(rec) for rec in
                                         worked_days_line_ids]
        self.commission_report_ids = [fields.Command.clear()]
        input_line_values = self.get_input_line_ids(employee_id, start_date, to_date)
        self.employee_payslip_input_ids = [fields.Command.clear()]
        self.employee_payslip_input_ids = [fields.Command.create(record) for
                                           record in input_line_values]
        return

    @api.model
    def create(self, vals):
        """Supering create function to add reference"""
        if vals.get('reference', 'New') == 'New':
            vals['reference'] = self.env['ir.sequence'].next_by_code(
                'employee.payslip') or 'New'
        return super(EmployeePayslip, self).create(vals)

    def unlink(self):
        """This function is used to check the payslip state when deleting
        the payslip, we can't delete a payslip that is not in the draft and cancelled state"""
        if any(self.filtered(
                lambda payslip: payslip.state not in ('draft', 'cancel'))):
            raise UserError(
                _('You cannot delete a payslip which is not draft or cancelled state!'))
        return super(EmployeePayslip, self).unlink()

    def action_register_payment(self):
        """ Register payment for the payslip's account move after necessary checks """
        net_rule = self.structure_id.employee_salary_rule_ids.filtered(
            lambda r: r.code == "NET")
        if not net_rule or not net_rule.account_credit_id:
            raise UserError(
                _('The NET salary rule or its credit account is not properly configured.'))
        if not net_rule.account_credit_id.reconcile:
            raise UserError(
                _('The credit account assigned to the NET salary rule must be reconciliable, but it is not.'))
        for rec in self:
            bank_account = rec.employee_id.sudo().bank_account_id
            if not bank_account:
                raise UserError(
                    _('No bank account is assigned to the employee.'))
            if not bank_account.allow_out_payment:
                raise UserError(
                    _('The employee\'s bank account is not marked as trusted for outgoing payments.'))

            # Proceed with posting and payment registration
            rec.account_move_id.write({'state': 'posted'})
            if rec.expense_sheet_ids:
                rec.expense_sheet_ids.write({
                    'state': 'done'
                })
            rec._compute_is_attachment_paid()
        return self.account_move_id.action_register_payment()

    def action_paid(self):
        """This method update payslip state to paid and if any gratuity
        settlement is applied for this payslip it's state will be also
        updated to paid"""
        for slip in self:
            slip.write({'state': 'paid'})
            if slip.expense_sheet_ids:
                slip.expense_sheet_ids.write({
                    'state': 'done',
                    'payment_state': 'paid'
                })
                slip.expense_sheet_ids.expense_line_ids.write({
                    'state': 'done',
                })
            if slip.gratuity_settlement_id:
                if slip.credit_note:
                    slip.gratuity_settlement_id.write({'state': 'cancel'})
                else:
                    slip.gratuity_settlement_id.write({'state': 'paid'})
            if all(slip.state == 'paid' for slip in slip.employee_payslip_batch_id.employee_payslip_ids):
                slip.employee_payslip_batch_id.write({'state': 'paid'})

    def action_cancel(self):
        """ Cancel payslip, its journal entry, and related payments """
        for slip in self:
            move = slip.account_move_id
            if move:
                reconciled_lines = move.line_ids._all_reconciled_lines()
                payments = reconciled_lines.mapped('payment_id').filtered(
                    lambda p: p)
                payments.filtered(
                    lambda p: p.state not in ('cancel', 'cancelled')).write(
                    {'state': 'cancel'})
                if move.state != 'cancel':
                    move.write({'state': 'cancel'})
        return self.write({'state': 'cancel'})

    def action_set_draft(self):
        """ Set the payslip and its journal entry to draft """
        for slip in self:
            move = slip.account_move_id
            if move:
                move.line_ids.filtered(
                    lambda l: l.matched_debit_ids or l.matched_credit_ids
                ).remove_move_reconcile()
                move.write({
                    'state': 'draft',
                    'line_ids': [fields.Command.clear()]
                })
        return self.write({'state': 'draft'})

    def action_refund(self):
        """Refunds the payslip"""
        refund_payslips = []
        for payslip in self:
            # Create a copy of the payslip with credit_note set to True
            refund_vals = {
                'credit_note': True,
                'payslip_name': _('Refund: ') + payslip.payslip_name,
                'contract_id': payslip.contract_id.id,
                'state': 'waiting'
            }
            refund_payslip = payslip.copy(refund_vals)
            refund_payslip.parent_id = self.id

            # Generate reference for the refund payslip
            reference = refund_payslip.reference or self.env[
                'ir.sequence'].next_by_code('employee.payslip')
            refund_payslip.write({'reference': reference})

            # Reverse worked days and input lines
            for worked_day in refund_payslip.employee_worked_days_ids:
                worked_day.write(
                    {'days': -worked_day.days, 'hour': -worked_day.hour})
            for payslip_input in refund_payslip.employee_payslip_input_ids:
                payslip_input.write({'amount': -payslip_input.amount})
            for payslip_line in refund_payslip.employee_payslip_line_ids:
                payslip_line.write({'amount': -payslip_line.amount,
                                    'total': -payslip_line.total})
            refund_payslips.append(refund_payslip)

        # Define views
        refund_form_view = self.env.ref(
            'cyllo_payroll_management.view_employee_payslip_form', False)
        refund_tree_view = self.env.ref(
            'cyllo_payroll_management.view_employee_payslip_tree', False)

        # Return action
        return {
            'name': _("Refund Payslip"),
            'view_mode': 'tree, form',
            'res_id': refund_payslips[0].id,
            'res_model': 'employee.payslip',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'domain': [('parent_id', '=', self.id)],
            'views': [(refund_form_view.id, 'form'),
                      (refund_tree_view.id, 'tree')],
            'context': {}
        }

    def action_create_entry(self):
        """ To create the account moves for the payslip """
        net_rule = self.structure_id.employee_salary_rule_ids.filtered(
            lambda r: r.code == "NET")
        if not net_rule or not net_rule.account_credit_id:
            raise UserError(
                _('The NET salary rule or its credit account is not properly configured.'))
        for payslip in self:
            if not payslip.account_move_id:
                account_move_vals = {'state': 'draft', 'date': payslip.to_date,
                                     'journal_id': payslip.journal_id.id}
                if payslip.is_batch_payslip:
                    account_move_vals['ref'] = payslip.batch_payslip_name
                else:
                    account_move_vals['ref'] = payslip.reference
                account_move = payslip.account_move_id.create(account_move_vals)
                payslip.account_move_id = account_move.id
            line_ids = []
            for line in payslip.employee_payslip_line_ids:
                if not line.account_credit_id and not line.account_debit_id:
                    continue
                if line.account_credit_id:
                    line_vals = {
                        'name': line.name,
                        'account_id': line.account_credit_id.id,
                        'debit': 0.0,
                        'credit': line.total,
                        'move_id': payslip.account_move_id.id,
                        'partner_id': payslip.employee_id.work_contact_id.id if line.code == "NET" else False,
                    }
                    if payslip.is_batch_payslip:
                        line_vals['batch_id'] = self.batch
                        line_count = self.env[
                            'account.move.line'].sudo().search_count(
                            [('batch_id', '=', self.batch)])
                        batch = self.env[
                            'employee.payslip.batch'].sudo().browse(self.batch)
                        batch.journal_entry_count = line_count
                    line_ids.append(fields.Command.create(line_vals))
                if line.account_debit_id:
                    line_vals = {
                        'name': line.name,
                        'account_id': line.account_debit_id.id,
                        'debit': line.total,
                        'credit': 0.0,
                        'move_id': payslip.account_move_id.id,
                        'partner_id': payslip.employee_id.work_contact_id.id if line.code == "NET" else False,
                    }
                    if payslip.is_batch_payslip:
                        line_vals['batch_id'] = self.batch
                    line_ids.append(fields.Command.create(line_vals))
            payslip.account_move_id.line_ids = line_ids
            # Reset report flag for commissions
            if payslip.commission_report_ids:
                payslip.commission_report_ids.write({'report_to_payslip': False})
                
            payslip.write({'state': 'done'})

            # Validating work entries within payslip dates
            for work in self:
                work_entries = self.env['hr.work.entry'].sudo().search(
                    [('employee_id', '=', work.employee_id.id),
                     ('date_start', '>=', work.start_date),
                     ('date_stop', '<=', work.to_date),
                     ('state', '!=', 'conflict')])
                work_entries.action_validate()

    def action_view_attendance(self):
        """To view corresponding attendance of the employee"""
        return {
            'name': 'Attendance',
            'view_mode': 'tree,form',
            'res_model': 'hr.attendance',
            'type': 'ir.actions.act_window',
            'domain': [('employee_id', '=', self.employee_id.id)],
        }

    def action_view_refund(self):
        """To view corresponding refund of the employee payslip"""
        return {
            'name': 'Refunds',
            'view_mode': 'tree,form',
            'res_model': 'employee.payslip',
            'type': 'ir.actions.act_window',
            'domain': [('parent_id', '=', self.id)],
        }

    def action_view_work_entry(self):
        """To view corresponding work entries of the employee"""
        return {
            'name': 'Work Entry',
            'view_mode': 'tree,form',
            'res_model': 'hr.work.entry',
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', self.work_entry_ids.ids)],
        }

    def action_link_expenses(self):
        """Link expense sheets to this payslip after computation"""
        for payslip in self:
            if payslip.expense_sheet_ids:
                payslip.expense_sheet_ids.write({'payslip_id': payslip.id})

    def action_link_commissions(self):
        """Link commission reports to this payslip after computation"""
        for payslip in self:
            if payslip.commission_report_ids:
                payslip.commission_report_ids.write({'payslip_id': payslip.id})

    def action_compute_sheet(self):
        """Compute the salary details for the selected employee."""
        for payslip in self:
            payslip._onchange_employee_id()
            if payslip.structure_id:
                payslip.employee_payslip_line_ids.unlink()
                contract_ids = payslip.contract_id.id or self.get_employee_contract(
                    payslip.employee_id, payslip.start_date, payslip.to_date)
                payslip.action_link_expenses()
                self.gratuity_settlement_id = False
                if self.gratuity_settlement_ids:
                    self.gratuity_settlement_id = self.gratuity_settlement_ids[
                        0]
                payslip.action_link_commissions()
                lines = [fields.Command.create(line) for line in
                         self._get_payslip_lines(contract_ids, payslip)]
                payslip.sudo().write(
                    {'employee_payslip_line_ids': lines, 'state': 'waiting'})
            else:
                raise ValidationError(_('Missing salary structure'))

    def get_date_from_schedule_pay(self):
        """ To get the end date from the scheduled pay of salary structure"""
        time_difference = timedelta(days=1)
        if self.structure_id.schedule_pay == 'daily':
            time_difference = timedelta(days=1)
        elif self.structure_id.schedule_pay == 'weekly':
            time_difference = relativedelta(weeks=1, days=-1)
        elif self.structure_id.schedule_pay == 'monthly':
            time_difference = relativedelta(months=1, days=-1)
        return time_difference

    @api.model
    def get_employee_contract(self, employee_id, start_date, to_date):
        """Get the contract of the employee based on certain conditions"""
        contracts = self.env['hr.contract'].sudo().search([
            ('employee_id', '=', employee_id.id), ('state', '=', 'open'), '|',
            '&', ('date_start', '<=', start_date),
            '|', ('date_end', '>=', to_date), ('date_end', '=', False),
            '&', ('date_end', '>=', start_date), ('date_start', '<=', to_date)])
        return contracts.ids

    def get_input_line_ids(self, employee, date_from, date_to):
        """To get the other input values"""
        input_line_values = []
        attachment = self.env['employee.salary.attachment'].sudo().search([
            ('employee_id', '=', employee.id), ('start_date', '<=', date_from),
            ('state', '=', 'running')])
        attachment_types = list(
            attachment.mapped('employee_payslip_other_input_id'))
        for record in attachment_types:
            attachments = attachment.filtered(
                lambda self: self.employee_payslip_other_input_id == record)
            is_attachment = True if attachments.employee_payslip_other_input_id != self.env.ref(
                'cyllo_payroll_management.employee_payslip_other_input_child_support') else False
            input_line_values.append({
                'type_id': attachments.employee_payslip_other_input_id.id,
                'code': attachments.employee_payslip_other_input_id.code,
                'amount': sum(attachments.mapped('active_amount')),
                'payslip_id': self.id,
                'is_attachment': is_attachment
            })
        expense_sheets = self.env['hr.expense.sheet'].sudo().search([
            ('employee_id', '=', employee.id),
            ('state', '=', 'approve'),
            ('report_to_payslip', '=', True),
            '|',
            ('payslip_id', '=', False),  # Not yet included in any payslip
            ('payslip_id', '=', self.id),  # Not yet included in other payslip
        ])

        if expense_sheets:
            total_expense_amount = sum(expense_sheets.mapped('total_amount'))
            expense_input_type = self.env.ref(
                'cyllo_payroll_management.employee_payslip_other_input_expense_reimbursement'
            )
            input_line_values.append({
                'type_id': expense_input_type.id,
                'code': expense_input_type.code,
                'amount': total_expense_amount,
                'payslip_id': self.id,
                'is_attachment': False
            })
            # Store expense sheets for reference
            for expense in expense_sheets:
                self.expense_sheet_ids = [(4, expense.id)]

        if employee.user_id:
            # Search for commissions manually marked for the next payslip
            commission_reports = self.env['commission.report'].sudo().search([
                ('user_id', '=', employee.user_id.id),
                ('plan_id.state', '=', 'approved'),
                ('report_to_payslip', '=', True),
                ('remaining_amount', '>', 0)
            ])

            if commission_reports:
                commission_input_type = self.env.ref(
                    'cyllo_payroll_management.employee_payslip_other_input_commission',
                    raise_if_not_found=False
                )
                if commission_input_type:
                    delta = sum(commission_reports.mapped('remaining_amount'))
                    if delta > 0:
                        input_line_values.append({
                                'type_id': commission_input_type.id,
                                'code': commission_input_type.code,
                                'amount': delta,
                                'payslip_id': self.id,
                                'is_attachment': False,
                        })
                    self.commission_report_ids = commission_reports

        # Add advance salary deductions
        advances = self.env['hr.advance.salary'].get_active_advances_for_employee(
            employee.id, date_from
        )
        if advances:
            deduction_input_type = self.env.ref(
                'cyllo_payroll_management.employee_payslip_other_input_deduction',
                raise_if_not_found=False
            )
            if not deduction_input_type:
                deduction_input_type = self.env['employee.payslip.other.input'].sudo().search([('code', '=', 'DED')], limit=1)

            if deduction_input_type:
                for advance in advances:
                    # Deduction starts from the NEXT month after approval
                    approval_start_of_month = advance.approval_date.replace(day=1)
                    payslip_start_of_month = date_from.replace(day=1)
                    
                    if advance.approval_date and payslip_start_of_month >= approval_start_of_month:
                        # Calculate deduction using the helper method from the model
                        deduction = min(advance._get_monthly_deduction_amount(contract=self.contract_id), advance.remaining_amount)

                        if deduction > 0:
                            # Link to or create a schedule line
                            payslip_month = date_from.replace(day=1)
                            schedule_line = self.env['hr.advance.salary.line'].sudo().search([
                                ('advance_id', '=', advance.id),
                                ('date', '=', payslip_month),
                                ('payslip_id', 'in', [False, self.id])
                            ], limit=1)
                            
                            if not schedule_line:
                                schedule_line = self.env['hr.advance.salary.line'].sudo().create({
                                    'advance_id': advance.id,
                                    'date': payslip_month,
                                    'amount': deduction,
                                    'payslip_id': self.id,
                                })
                            else:
                                schedule_line.sudo().write({
                                    'payslip_id': self.id,
                                    'amount': deduction, # Update planned amount with actual
                                })

                            input_line_values.append({
                                'type_id': deduction_input_type.id,
                                'code': deduction_input_type.code,
                                'amount': -deduction,
                                'payslip_id': self.id,
                                'is_attachment': False,
                                'advance_salary_id': advance.id,
                            })
        return input_line_values

    @api.model
    def get_worked_day_lines(self, employee_id, start_date, to_date,
                             employee_contract):
        """Calculate the worked days and work entries"""
        employee_contract.generate_work_entries(start_date, to_date)
        work_entry_values = []
        work_entries = self.env['hr.work.entry'].sudo().search([
            ('employee_id', '=', employee_id.id),
            ('date_start', '>=', start_date),
            ('date_stop', '<=', to_date),
            ('state', '!=', 'conflict'),
            ('contract_id', '=', employee_contract.id)
        ]).filtered(lambda
                        w: w.work_entry_source == employee_contract.work_entry_source)
        hours_per_day = employee_contract.resource_calendar_id.hours_per_day
        for record in work_entries.mapped('work_entry_type_id'):
            work_time = sum(work.duration for work in work_entries if
                            work.work_entry_type_id == record)
            days = self.calculate_days(work_time, hours_per_day,
                                       record.round_days, record.round_type)
            work_entry_values.append({
                'type': record.name,
                'work_entry_type_id': record.id,
                'sequence': record.sequence,
                'code': record.code,
                'days': days,
                'hour': work_time,
                'contract_id': employee_contract.id,
            })
        return work_entry_values

    def calculate_days(self, work_time, hours_per_day, round_days, round_type):
        """Calculate the days based on work time and hours per day"""
        days = round(work_time / hours_per_day, 5) if hours_per_day else 0
        if round_days == 'half':
            days = self.round_days_half(days, round_type)
        elif round_days == 'full':
            days = self.round_days_full(days, round_type)
        return days

    def round_days_half(self, days, round_type):
        """Round days to the nearest half"""
        if round_type == 'down':
            days = math.floor(days * 2) / 2
        elif round_type == 'up':
            days = math.ceil(days * 2) / 2
        else:
            decimal_part = days - int(days)
            if 0.25 <= decimal_part < 0.5:
                days = math.ceil(days * 2) / 2
            elif decimal_part >= 0.75:
                days = math.ceil(days * 2) / 2
            else:
                days = math.floor(days * 2) / 2
        return days

    def round_days_full(self, days, round_type):
        """Round days to the nearest full"""
        if round_type == 'down':
            days = math.floor(days)
        elif round_type == 'up':
            days = math.ceil(days)
        else:
            decimal_part = days - int(days)
            if decimal_part >= 0.5:
                days = math.ceil(days)
            else:
                days = math.floor(days)
        return days

    def get_employee_cost_by_period(self, period_type='month'):
        """
        period_type:
            'month' -> current month
            'year'  -> current year
        """

        today = fields.Date.today()

        # Define date range
        if period_type == 'month':
            date_from = today.replace(day=1)
            date_to = (date_from + relativedelta(months=1)) - relativedelta(
                days=1)
        
        elif period_type == 'day':
            # date_from = today
            # date_to = today
            # For 'day', we want to see what was PROCESSED/CREATED today.
            # Using create_date to filter.
            payslips = self.search([
                ('create_date', '>=', today),
                ('state', 'in', ['done', 'paid'])
            ])
            
            # Skip the date_from/date_to search block below
            result = defaultdict(float)
            for slip in payslips:
                emp_name = slip.employee_id.name
                result[emp_name] += slip.total_amount

            labels = list(result.keys())
            data = list(result.values())
            return {'labels': labels, 'data': data}

        else:  # year
            date_from = today.replace(month=1, day=1)
            date_to = today.replace(month=12, day=31)

        # Fetch payslips inside range
        payslips = self.search([
            ('start_date', '>=', date_from),
            ('to_date', '<=', date_to),
            ('state', 'in', ['done', 'paid'])
        ])

        result = defaultdict(float)

        # Sum cost per employee
        for slip in payslips:
            emp_name = slip.employee_id.name
            result[emp_name] += slip.total_amount

        labels = list(result.keys())
        data = list(result.values())

        return {
            'labels': labels,
            'data': data,
        }

    def get_payroll_distribution_by_period(self, period_type='month'):
        """
        Calculates payroll distribution (Pie Chart) for a specific period.
        period_type: 'month' or 'year'
        """
        today = fields.Date.today()
        if period_type == 'month':
            date_from = today.replace(day=1)
            date_to = (date_from + relativedelta(months=1)) - relativedelta(days=1)
        elif period_type == 'day':
             # For 'day', we want to see what was PROCESSED/CREATED today.
            payslips = self.search([
                ('create_date', '>=', today),
                ('state', 'in', ['done', 'paid'])
            ])
            # Skip the date_from/date_to search block below.
            # We need to explicitly return here or restructure to avoid the second search.
            dist = defaultdict(float)
            type_map = {}
            for slip in payslips:
                struct = slip.structure_id
                key = struct.name if struct else 'Other'
                dist[key] += slip.total_amount
                if struct and struct.type_id:
                     type_map[key] = struct.type_id.id
            
            labels = list(dist.keys())
            data = list(dist.values())
            type_ids = [type_map.get(label, False) for label in labels]
            return {'labels': labels, 'data': data, 'type_ids': type_ids}

        else:  # year
            date_from = today.replace(month=1, day=1)
            date_to = today.replace(month=12, day=31)

        payslips = self.search([
            ('start_date', '>=', date_from),
            ('to_date', '<=', date_to),
            ('state', 'in', ['done', 'paid'])
        ])

        dist = defaultdict(float)
        type_map = {}

        for slip in payslips:
            struct = slip.structure_id
            key = struct.name if struct else 'Other'
            dist[key] += slip.total_amount
            
            # For the click action (openStructureType), we ideally want the structure TYPE id.
            if struct and struct.type_id:
                 type_map[key] = struct.type_id.id

        labels = list(dist.keys())
        data = list(dist.values())
        
        # Prepare type_ids aligned with labels
        type_ids = [type_map.get(label, False) for label in labels]

        return {
            'labels': labels,
            'data': data,
            'type_ids': type_ids
        }

    @api.model
    def get_payroll_dashboard_data(self):
        # ----------------- CARD VALUES (GLOBAL / CURRENT) -----------------
        employees = self.env['hr.employee'].search_count([])
        contracts = self.env['hr.contract'].search_count([('state', '=', 'open')])
        
        # ----------------- PERIOD STATS (YEAR vs MONTH) -----------------
        def get_stats_by_range(date_from, date_to):
            domain_generated = [
                ('start_date', '>=', date_from),
                ('to_date', '<=', date_to)
            ]
            domain_paid = domain_generated + [('state', '=', 'paid')]
            
            return {
                'generated': self.search_count(domain_generated),
                'paid': self.search_count(domain_paid)
            }

        today = fields.Date.today()
        
        # Year Range
        year_start = today.replace(month=1, day=1)
        year_end = today.replace(month=12, day=31)
        stats_year = get_stats_by_range(year_start, year_end)
        
        # Month Range
        month_start = today.replace(day=1)
        month_end = (month_start + relativedelta(months=1)) - relativedelta(days=1)
        stats_month = get_stats_by_range(month_start, month_end)

        # Day Range (Today - Activity Based)
        # Generated: Created Today
        generated_today = self.search_count([
            ('create_date', '>=', today)
        ])
        
        # Paid: Paid Today (Approximate using write_date + state check, or just Paid state + Write Date match)
        # Since we don't have a specific 'payment_date', we check if it's currently paid and was updated today.
        paid_today = self.search_count([
            ('state', '=', 'paid'),
            ('write_date', '>=', today)
        ])
        
        stats_today = {
            'generated': generated_today,
            'paid': paid_today
        }

        # ----------------- WARNINGS -----------------
        warnings_list = []

        draft_payslips = self.search([('state', '=', 'draft')])
        if draft_payslips:
            warnings_list.append({
                'label': 'Draft Payslips',
                'count': len(draft_payslips),
            })

        employees_without_contract = self.env['hr.employee'].search([
            ('contract_id', '=', False)
        ])
        if employees_without_contract:
            warnings_list.append({
                'label': 'Employees Without Running Contracts',
                'count': len(employees_without_contract),
            })

        both_contract_count = 0
        all_employees = self.env['hr.employee'].search([])

        for emp in all_employees:
            open_contract = self.env['hr.contract'].search_count([
                ('employee_id', '=', emp.id),
                ('state', '=', 'open')
            ])
            draft_contract = self.env['hr.contract'].search_count([
                ('employee_id', '=', emp.id),
                ('state', '=', 'draft')
            ])

            if open_contract and draft_contract:
                both_contract_count += 1

        if both_contract_count:
            warnings_list.append({
                'label': 'Employees With Both New And Running Contracts',
                'count': both_contract_count,
            })
        # Employees Without Bank Accounts
        employees_without_bank = self.env['hr.employee'].search([
            ('bank_account_id', '=', False)
        ])

        if employees_without_bank:
            warnings_list.append({
                'label': 'Employees Without Bank Accounts',
                'count': len(employees_without_bank),
            })

        # Nearly Expired Contracts (Next 30 Days)
        next_30_days = today + timedelta(days=30)

        nearly_expired_contracts = self.env['hr.contract'].search([
            ('date_end', '!=', False),
            ('date_end', '>=', today),
            ('date_end', '<=', next_30_days),
            ('state', '=', 'open')
        ])
        if nearly_expired_contracts:
            warnings_list.append({
                'label': 'Nearly Expired Contracts (Next 30 Days)',
                'count': len(nearly_expired_contracts),
            })
        employees_wo_id = self.env['hr.employee'].search([
            ('identification_id', '=', False),
        ])
        if employees_wo_id:
            warnings_list.append({
                'label': 'Employees Without Identification Number',
                'count': len(employees_wo_id),
            })

        # ----------------- PAYROLL BATCHES -----------------
        # batch_list = []  # remove if batch tracking not present
        batches = self.env['employee.payslip.batch'].search(
            [],
            order="id desc",
            limit=10
        )

        batch_list = []
        for batch in batches:
            batch_list.append({
                'id': batch.id,
                'name': batch.name,
                'state': batch.state,
                # ✅ CORRECT FIELD
                'payslip_count': len(batch.employee_payslip_ids),
            })

        # ----------------- EMPLOYEE COST -----------------
        employee_cost_year = self.get_employee_cost_by_period('year')
        employee_cost_month = self.get_employee_cost_by_period('month')
        employee_cost_day = self.get_employee_cost_by_period('day')

        # ----------------- PAYROLL DISTRIBUTION -----------------
        payroll_dist_year = self.get_payroll_distribution_by_period('year')
        payroll_dist_month = self.get_payroll_distribution_by_period('month')
        payroll_dist_day = self.get_payroll_distribution_by_period('day')

        # ----------------- RETURN DATA -----------------
        return {
            'employees': employees,
            'contracts': contracts,
            # Init with Year values as default
            'generated': stats_year['generated'],
            'paid': stats_year['paid'],
            
            # Pass full stats for checking in frontend
            'stats_year': stats_year,
            'stats_month': stats_month,
            'stats_day': stats_today,

            'warnings': warnings_list,
            'batches': batch_list,
            'employee_cost_year_labels': employee_cost_year['labels'],
            'employee_cost_year_data': employee_cost_year['data'],

            'employee_cost_month_labels': employee_cost_month['labels'],
            'employee_cost_month_data': employee_cost_month['data'],
            
            'employee_cost_day_labels': employee_cost_day['labels'],
            'employee_cost_day_data': employee_cost_day['data'],

            'payroll_dist_year_labels': payroll_dist_year['labels'],
            'payroll_dist_year_data': payroll_dist_year['data'],
            'payroll_dist_year_type_ids': payroll_dist_year['type_ids'],

            'payroll_dist_month_labels': payroll_dist_month['labels'],
            'payroll_dist_month_data': payroll_dist_month['data'],
            'payroll_dist_month_type_ids': payroll_dist_month['type_ids'],
            
            'payroll_dist_day_labels': payroll_dist_day['labels'],
            'payroll_dist_day_data': payroll_dist_day['data'],
            'payroll_dist_day_type_ids': payroll_dist_day['type_ids'],
        }

    @api.model
    def _get_payslip_lines(self, contract_ids, payslip):
        """ Method to calculate salary line when computing the sheet"""

        def _sum_salary_rule_category(localdict, category, amount):
            """To get the all items based on the python code"""
            if category.parent_id:
                localdict = _sum_salary_rule_category(localdict,
                                                      category.parent_id,
                                                      amount)
            localdict['categories'].dict[category.code] = (
                        category.code in localdict[
                    'categories'].dict and localdict['categories'].dict[
                            category.code] + amount or amount)
            return localdict

        class BrowsableObject(object):
            """A browsable object capable of dynamically retrieving attributes. The `__getattr__} method can be
            used to obtain specific attributes of an object, which this class represents. The value of the property
            is returned if it is present in the dictionary; if not, a default value of 0.0 is returned."""

            def __init__(self, employee_id, dict, env):
                """Initialize the BrowsableObject.
                   @param employee_id (int): The employee ID associated with the
                   object.
                   @param dict (dict): The dictionary containing attributes and
                   their corresponding values.
                   @param env (env): The Odoo environment for the object.
                   """
                self.employee_id = employee_id
                self.dict = dict
                self.env = env

            def __getattr__(self, attr):
                """Get the value of the requested attribute.
                    @param attr(str): The name of the attribute to retrieve.
                    @return (float): The value of the requested attribute or
                    0.0 if not found. """
                return attr in self.dict and self.dict.__getitem__(attr) or 0.0

        class InputLine(BrowsableObject):
            """A class that will be used into the python code, mainly for usability purposes"""

            def sum(self, code, from_date, to_date=None):
                to_date = fields.Date.today() if to_date is None else to_date
                self.env.cr.execute("""
                                    SELECT sum(amount) as sum
                                    FROM employee_payslip as hp, employee_payslip_input as pi
                                    WHERE hp.employee_id = %s
                                      AND hp.state = 'done'
                                      AND hp.start_date >= %s
                                      AND hp.to_date <= %s
                                      AND hp.id = pi.employee_payslip_id
                                      AND pi.code = %s""",
                                    (self.employee_id, from_date, to_date,
                                     code))
                return self.env.cr.fetchone()[0] or 0.0

        class WorkedDays(BrowsableObject):
            """A class that will be used into the python code, mainly for usability purposes """

            def _sum(self, code, from_date, to_date=None):
                to_date = fields.Date.today() if to_date is None else to_date

                self.env.cr.execute("""
                                    SELECT sum(days) as number_of_days,
                                           sum(hour) as number_of_hours
                                    FROM employee_payslip as hp,
                                         employee_worked_days as pi
                                    WHERE hp.employee_id = %s
                                      AND hp.state = 'done'
                                      AND hp.start_date >= %s
                                      AND hp.to_date <= %s
                                      AND hp.id = pi.employee_payslip_id
                                      AND pi.code = %s""",
                                    (self.employee_id, from_date, to_date,
                                     code))
                return self.env.cr.fetchone()

            def sum(self, code, from_date, to_date=None):
                res = self._sum(code, from_date, to_date)
                return res and res[0] or 0.0

            def sum_hours(self, code, from_date, to_date=None):
                res = self._sum(code, from_date, to_date)
                return res and res[1] or 0.0

        class Payslips(BrowsableObject):
            """A class that will be used into the python code, mainly for usability purposes"""

            def sum(self, code, from_date, to_date=None):
                to_date = fields.Date.today() if to_date is None else to_date
                self.env.cr.execute("""SELECT sum(
                                                      case
                                                          when hp.credit_note = False
                                                              then (pl.total)
                                                          else (-pl.total) end)
                                       FROM employee_payslip as hp,
                                            employee_payslip_line
                                                as pl
                                       WHERE hp.employee_id = %s
                                         AND hp.state = 'done'
                                         AND hp.start_date >= %s
                                         AND hp.to_date <= %s
                                         AND hp.id = pl.employee_payslip_id
                                         AND pl.code = %s""",
                                    (self.employee_id, from_date, to_date,
                                     code))
                res = self.env.cr.fetchone()
                return res and res[0] or 0.0

        # This functions and the variable are used to compute the salary rules
        # based on the conditions that we have given inside the rules
        result_dict = {}
        rules_dict = {}
        worked_days_dict = {}
        inputs_dict = {}
        blacklist = []
        for worked_days_line in payslip.employee_worked_days_ids:
            worked_days_dict[worked_days_line.code] = worked_days_line
        for input_line in payslip.employee_payslip_input_ids:
            if input_line.code:

                inputs_dict[input_line.code] = input_line.code
        inputs_dict = {line.code: line.amount for line in
                       self.employee_payslip_input_ids if line.code}

        categories = BrowsableObject(payslip.employee_id.id, {}, self.env)

        inputs = InputLine(payslip.employee_id.id, inputs_dict, self.env)

        worked_days = WorkedDays(payslip.employee_id.id, worked_days_dict,
                                 self.env)

        payslips = Payslips(payslip.employee_id.id, payslip, self.env)

        rules = BrowsableObject(payslip.employee_id.id, rules_dict, self.env)

        baselocaldict = {'categories': categories, 'rules': rules,
                         'payslip': payslips,
                         'worked_days': worked_days, 'inputs': inputs}

        contracts = self.env['hr.contract'].sudo().browse(contract_ids)

        if len(contracts) == 1 and payslip.structure_id:
            structure_ids = list(
                set(payslip.structure_id._get_parent_structure().ids))

        else:
            structure_ids = contracts.get_all_structures()

        rule_ids = self.env['employee.salary.structure'].sudo().browse(
            structure_ids)._get_all_rules()

        sorted_rule_ids = [id for id, sequence in
                           sorted(rule_ids, key=lambda x: x[1])]

        sorted_rules = self.env['employee.salary.rule'].browse(sorted_rule_ids)

        for contract in contracts:
            employee = contract.employee_id
            localdict = dict(baselocaldict, employee=employee,
                             contract=contract)
            for rule in sorted_rules:

                key = rule.code + '-' + str(contract.id)
                localdict['result'] = None
                localdict['result_qty'] = 1.0
                localdict['result_rate'] = 100
                if rule._satisfy_condition(
                        localdict) and rule.id not in blacklist:
                    amount, qty, rate = rule._compute_rule(localdict)
                    # Enforce that rules in the Deduction category are strictly negative.
                    if (rule.category_id.code or '').upper() == 'DED' and amount > 0:
                        amount = -amount
                    previous_amount = rule.code in localdict and localdict[
                        rule.code] or 0.0
                    tot_rule = amount * qty * rate / 100.0
                    localdict[rule.code] = tot_rule
                    rules_dict[rule.code] = rule
                    localdict = _sum_salary_rule_category(localdict,
                                                          rule.category_id,
                                                          tot_rule - previous_amount)
                    result_dict[key] = {
                        'employee_salary_rule_id': rule.id,
                        'contract_id': contract.id,
                        'name': rule.name,
                        'code': rule.code,
                        'category_id': rule.category_id.id,
                        'sequence': rule.sequence,
                        'appears_on_payslip': rule.appears_on_payslip,
                        'condition_select': rule.condition_select,
                        'condition_python': rule.condition_python,
                        'condition_range': rule.condition_range,
                        'condition_range_min': rule.condition_range_min,
                        'condition_range_max': rule.condition_range_max,
                        'amount_select': rule.amount_select,
                        'amount_fix': rule.amount_fix,
                        'amount_python_compute': rule.amount_python_compute,
                        'amount_percentage': rule.amount_percentage,
                        'amount_percentage_base': rule.amount_percentage_base,
                        'partner_id': rule.partner_id.id,
                        'amount': amount,
                        'employee_id': contract.employee_id.id,
                        'quantity': qty,
                        'rate': rate,
                    }
                else:
                    blacklist += [id for id, seq in
                                  rule._recursive_search_of_rules()]
        return list(result_dict.values())

    def get_batch_payslips(self, date_from, date_to, employee_id=False,
                           contract_id=False):
        """To get the batch payslip"""
        res = {
            'value': {
                'employee_payslip_line_ids': [],
                'employee_payslip_input_ids': [fields.Command.delete(x) for x in
                                               self.employee_payslip_input_ids.ids],
                'employee_worked_days_ids': [fields.Command.delete(x) for x in
                                             self.employee_worked_days_ids.ids],
                'payslip_name': '',
                'contract_id': False,
                'structure_id': False,
            }
        }
        if not (employee_id and date_from and date_to):
            return res
        ttyme = datetime.combine(fields.Date.from_string(date_from), time.min)
        employee = self.env['hr.employee'].browse(employee_id)
        locale = self.env.context.get('lang') or 'en_US'
        payslip_name = _('Pay Slip of %s for %s') % (employee.name, tools.ustr(
            babel.dates.format_date(
                date=ttyme, format='MMMM-y', locale=locale)))
        res['value'].update({'payslip_name': payslip_name,
                             'company_id': employee.company_id.id})
        if not contract_id:
            contract = self.get_employee_contract(employee, date_from, date_to)
            if not contract:
                return res
            res['value'].update({'contract_id': contract})
        contract_id = self.env['hr.contract'].sudo().browse(contract)
        structure = contract_id.employee_salary_structure_id
        if not structure:
            return res
        employee_worked_days_line_ids = self.get_worked_day_lines(employee,
                                                                  date_from,
                                                                  date_to,
                                                                  contract_id)
        employee_input_line_ids = self.get_input_line_ids(employee, date_from, date_to)
        res['value'].update({'structure_id': structure.id,
                             'employee_worked_days_ids': employee_worked_days_line_ids,
                             'employee_payslip_input_ids': employee_input_line_ids})
        return res


class EmployeeWorkedDays(models.Model):
    """To get the worked days and hours of the employee"""
    _name = 'employee.worked.days'
    _description = 'Employee Worked Days'

    type = fields.Char(string='Name')
    days = fields.Float(string='Working Days')
    hour = fields.Float(string='Working Hours')
    company_id = fields.Many2one('res.company', required=True,
                                 default=lambda self: self.env.company)
    currency_id = fields.Many2one(comodel_name='res.currency', default=lambda
        self: self.env.company.currency_id.id)
    contract_id = fields.Many2one(required=True,
                                  related='employee_payslip_id.contract_id',
                                  help="The contract for which applied this input")
    work_entry_type_id = fields.Many2one('hr.work.entry.type', string='Type',
                                         help="The type of work entry")
    code = fields.Char(required=True, related='work_entry_type_id.code',
                       help="The code that can be used in the salary rules")
    amount = fields.Float(string='Total Amount',
                          help='To add the cost to company',
                          compute='_compute_amount')
    sequence = fields.Integer(required=True, index=True, default=10,
                              help="Sequence of the work")
    is_paid = fields.Boolean(string='Paid Option',
                             help='Checking the work entry type is paid',
                             compute='_compute_is_paid', store=True)
    employee_payslip_id = fields.Many2one('employee.payslip', string='Payslip')

    @api.depends('hour', 'days', 'employee_payslip_id',
                 'employee_payslip_id.structure_id',
                 'employee_payslip_id.employee_id')
    def _compute_amount(self):
        """Compute the total amount"""
        for rec in self:
            amount = 0
            if rec.is_paid:
                if rec.contract_id and rec.contract_id.wage_type in ["hourly",
                                                                     "monthly",
                                                                     False]:
                    if rec.contract_id.wage_type == "hourly":
                        amount = rec.employee_payslip_id.contract_id.hourly_wage * rec.hour
                    elif rec.contract_id.wage_type == "monthly" or not rec.contract_id.wage_type:
                        total_worked_hours = abs(
                            rec.employee_payslip_id.total_worked_hours)
                        if total_worked_hours:
                            amount = rec.contract_id.wage * rec.hour / total_worked_hours
            rec.amount = amount

    @api.depends('work_entry_type_id', 'employee_payslip_id',
                 'employee_payslip_id.structure_id',
                 'employee_payslip_id.employee_id')
    def _compute_is_paid(self):
        """Compute if the work entry is payable or not"""
        for record in self:
            if not record.employee_payslip_id.structure_id:
                record.is_paid = False
                continue
            unpaid_structure_ids = record.work_entry_type_id.unpaid_structure_ids.ids
            record.is_paid = record.employee_payslip_id.structure_id.id not in unpaid_structure_ids


class EmployeePayslipLine(models.Model):
    """To get the salary rules """

    _name = 'employee.payslip.line'
    _inherit = 'employee.salary.rule'
    _description = 'Employee Payslip Line'
    _order = 'contract_id, sequence'

    employee_payslip_id = fields.Many2one('employee.payslip',
                                          ondelete='cascade', required=True,
                                          help="To get te payslip values")
    employee_salary_rule_id = fields.Many2one('employee.salary.rule',
                                              string='Rule', required=True,
                                              help="To get the salary rule")
    name = fields.Char(string='Description', help='To add the name of the rule',
                       required=True, related='employee_salary_rule_id.name')
    code = fields.Char(help='To add the code', required=True,
                       related='employee_salary_rule_id.code')
    employee_id = fields.Many2one('hr.employee', required=True,
                                  help=" To Select the Employee")
    contract_id = fields.Many2one('hr.contract', required=True, index=True,
                                  help="Choose the Contract")
    category_id = fields.Many2one('employee.salary.rule.category',
                                  string='Rule Category',
                                  help='To add the category', required=True)
    rate = fields.Float(string='Rate (%)',
                        help='To get the percentage value from payroll',
                        digits=decimal.get_precision('Payroll Percentage'),
                        default=100.0)
    amount = fields.Float(digits=decimal.get_precision('Payroll Fixed Amount'),
                          help='Amount To the payslip')
    quantity = fields.Float(default=1.0, digits=decimal.get_precision(
        'Payroll Fixed Amount'),
                            help='Quantity in the payslip')
    total = fields.Float(compute='_compute_total',
                         help="Total of item applied to payslip",
                         digits=decimal.get_precision('Payroll Fixed Amount'),
                         store=True)
    account_debit_id = fields.Many2one(string='Debit Account',
                                       related='employee_salary_rule_id.account_debit_id',
                                       help='The debit account for journal entry posted')
    account_credit_id = fields.Many2one(string='Credit Account',
                                        related='employee_salary_rule_id.account_credit_id',
                                        help='The credit account for journal entry posted')

    @api.depends('quantity', 'amount', 'rate')
    def _compute_total(self):
        """The method is used to compute the total amount in the payslip"""
        for total in self:
            total.total = float(
                total.quantity) * total.amount * total.rate / 100

    @api.model_create_multi
    def create(self, vals_list):
        """ To makesure that there is contract exist at the time of creation"""
        for values in vals_list:
            if 'employee_id' not in values or 'contract_id' not in values:
                payslip = self.env['employee.payslip'].browse(
                    values.get('employee_payslip_id'))
                values['employee_id'] = values.get(
                    'employee_id') or payslip.employee_id.id
                values['contract_id'] = values.get(
                    'contract_id') or payslip.contract_id.id
                if not values['contract_id']:
                    raise ValidationError(
                        _('You need to set the contract for the salary line '))
        return super(EmployeePayslipLine, self).create(vals_list)


class EmployeePayslipInput(models.Model):
    """The input values for the payslip computation are stored in this model.
    Every record is an input related to a payslip, which may include
    additional customised elements, deductions, or allowances."""
    _name = 'employee.payslip.input'
    _description = 'Payslip Input'
    _order = 'payslip_id'

    payslip_id = fields.Many2one('employee.payslip', string='Pay Slip',
                                 ondelete='cascade', help="Payslip the input",
                                 index=True)
    type_id = fields.Many2one('employee.payslip.other.input',
                              help='The Type of other input in payslip',
                              domain="['|',('structure_ids','=',False), ('id','in',allowed_type_ids)]")
    allowed_type_ids = fields.Many2many(string='Allowed Input Type',
                                        help='The allowed input types for the current payslip',
                                        related='payslip_id.structure_id.other_input_line_type_ids')
    sequence = fields.Integer(required=True, index=True, default=10,
                              help="Sequence of salary rule the")
    code = fields.Char(required=True, related='type_id.code',
                       help="The code that can be used in the salary rules")
    company_id = fields.Many2one('res.company', required=True,
                                 default=lambda self: self.env.company,
                                 help='Select the company')
    currency_id = fields.Many2one(related='company_id.currency_id',
                                  help='Currency of company')
    amount = fields.Monetary(help="It is used in computation.")
    is_attachment = fields.Boolean(string='Attachment Input',
                                   help='This enables the attachment')
    advance_salary_id = fields.Many2one(
        'hr.advance.salary',
        string='Advance Salary',
        help='Link to the advance salary record this deduction is for',
        ondelete='set null'
    )
    commission_report_id = fields.Many2one(
        'commission.report',
        string='Commission Report',
        help='Link to the commission report this input is for',
        ondelete='set null'
    )
