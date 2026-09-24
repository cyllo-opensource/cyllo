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
import calendar
from datetime import date

from odoo import _,api, fields, models
from odoo.tools import date_utils


class EmployeePayslipBatch(models.Model):
    """ The model is used to generate the payslip batch wise"""
    _name = 'employee.payslip.batch'
    _description = 'Employee Payslip Batches'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(required=True, help='Name for the batch payslip')
    employee_payslip_ids = fields.One2many('employee.payslip', 'employee_payslip_batch_id',
                                           string='The payslips that in the batch', help='Payslip related to this batch')
    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirmed'), ('done', 'Done'), ('paid', 'Paid'),],
                             string='Status', index=True, readonly=True, copy=False,
                             default='draft', help='State of the batch')
    start_date = fields.Date(string='Date From', required=True, help="Start date of batch payslip period",
                             default=lambda self: fields.Date.to_string(date.today().replace(day=1)))
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    end_date = fields.Date(string='Date To', required=True, help="End date of batch payslip period",
                           compute='_compute_end_date')
    is_batch_payslip = fields.Boolean(string='Batch Payslip Enabled', default=False,
                                      help="If its checked, indicates that it generated batch payslip")
    journal_entry_count = fields.Integer(help='Count of journal entries of payslip', compute='_compute_journal_entry_count', store=True)
    batch_move_line = fields.Boolean(string='Batch Payroll Move Line', related='company_id.batch_move_line')

    @api.depends('start_date')
    def _compute_end_date(self):
        """ Compute method to calculate the end date of the batch payslip"""
        for record in self:
            if record.start_date:
                end_of_month = calendar.monthrange(record.start_date.year, record.start_date.month)[1]
                record.end_date = record.start_date.replace(day=end_of_month)
            else:
                record.end_date = date_utils.end_of(fields.Date.today(), 'month')

    @api.depends('employee_payslip_ids', 'employee_payslip_ids.account_move_id', 'state')
    def _compute_journal_entry_count(self):
        """Compute the count of journal entries for the batch"""
        for batch in self:
            if batch.batch_move_line and batch.state in ('done', 'paid'):
                # For batch with batch_move_line, count move lines with batch_id
                batch.journal_entry_count = self.env['account.move.line'].search_count([
                    ('batch_id', '=', batch.id)
                ])
            elif not batch.batch_move_line and batch.employee_payslip_ids:
                # For batch without batch_move_line, count move lines from individual payslips
                move_ids = batch.employee_payslip_ids.mapped('account_move_id')
                batch.journal_entry_count = self.env['account.move.line'].search_count([
                    ('move_id', 'in', move_ids.ids)
                ])
            else:
                batch.journal_entry_count = 0

    def action_draft(self):
        """ To rest into draft"""
        self.employee_payslip_ids.action_set_draft()
        return self.write({'state': 'draft'})


    def action_generate_batch(self):
        """This method is used to generate the payslip batch wise, that we
        selected in the batch list"""
        self.is_batch_payslip = True
        action = self.env["ir.actions.actions"]._for_xml_id(
            "cyllo_payroll_management.action_view_employee_payslip_batch_list")
        return action

    def action_create_entry(self):
        """To generate the journal entry for the payslip"""
        self.write({'state': 'done'})
        for data in self.employee_payslip_ids:
            data.write({'batch': self.id})
            data.action_create_entry()

    def action_validate(self):
        """To create the move entry for the batch payslip if the batch move line is enabled"""
        payslip_ids = self.employee_payslip_ids
        amount_total = {}
        # Calculate total amounts for each type of entry
        for payslip in payslip_ids:
            sorted_lines = sorted(payslip.employee_payslip_line_ids,
                                  key=lambda line: line.id)
            for line in sorted_lines:
                if line.name in amount_total:
                    amount_total[line.name] += line.total
                else:
                    amount_total[line.name] = line.total
        # Create the account move
        account_move_vals = {
            'state': 'draft',
            'date': payslip_ids[0].to_date,
            'journal_id': payslip_ids[0].journal_id.id,
            'ref': payslip_ids[0].batch_payslip_name if payslip_ids[0].is_batch_payslip else payslip_ids[0].reference,
        }
        account_move = self.env['account.move'].create(account_move_vals)
        journal_item_ids = []
        line_ids = []
        # Create journal items for each type of entry
        for entry_name, total_amount  in amount_total.items():
            debit_lines = payslip_ids.employee_payslip_line_ids.filtered(lambda line: line.name.strip() == entry_name and line.account_debit_id)
            credit_lines = payslip_ids.employee_payslip_line_ids.filtered(lambda line: line.name.strip() == entry_name and line.account_credit_id)
            if debit_lines:
                line_vals = {
                    'name': entry_name,
                    'account_id': debit_lines[0].account_debit_id.id,
                    'debit': total_amount,
                    'credit': 0.0,
                    'move_id': account_move.id,
                    'batch_id': self.id
                }
                line_ids.append(fields.Command.create(line_vals))
            if credit_lines:
                line_vals = {
                    'name': entry_name,
                    'account_id': credit_lines[0].account_credit_id.id,
                    'debit': 0.0,
                    'credit': total_amount,
                    'move_id': account_move.id,
                    'batch_id': self.id
                }
                line_ids.append(fields.Command.create(line_vals))

        account_move.line_ids = line_ids
        payslip_ids.account_move_id = account_move.id
        payslip_ids.write({'state': 'done'})
        self.write({'state': 'done'})

    def action_register_payment(self):
        """ This method posts the journal entry for the payslip and updates its state to paid"""
        move_id = self.employee_payslip_ids[0].account_move_id
        move_id.write({'state': 'posted'})
        return move_id.action_register_payment()

    def action_create_payment(self):
        """This method open the wizard for payment registration of batch
        payslip"""
        view = self.env.ref("cyllo_payroll_management.view_employee_payslip_tree_register_payment")
        return {
            'name': _('Select Payslips'),
            'type': 'ir.actions.act_window',
            'view_mode': 'list',
            'view': view,
            'views': [(view.id, 'tree')],
            'res_model': 'employee.payslip',
            'target': 'new',
            'domain': [
                ('id', 'in', self.employee_payslip_ids.ids),
                ('state', '=', 'done')
            ],
        }

    def action_paid(self):
        """This method update the state of batch payslip and the payslip included
        in this batch"""
        self.write({'state': 'paid'})
        self.employee_payslip_ids.action_paid()

    def action_view_journal_entry(self):
        """To view corresponding journal entry"""
        return {
            'name': 'Journal Entry',
            'view_mode': 'tree,form',
            'res_model': 'account.move.line',
            'views': [[self.env.ref('account.view_move_line_tree').id, 'list'], [False, 'form']],
            'context': {'search_default_group_by_move': 1},
            'type': 'ir.actions.act_window',
            'domain': [('batch_id', '=', self.id)],
        }

    def mark_fully_paid(self):
        """This method open a confirmation wizard to confirm the mark as fully
        paid function"""
        self.is_batch_payslip = True
        action = self.env["ir.actions.actions"]._for_xml_id(
            "cyllo_payroll_management.action_view_employee_payslip_batch_mark_paid")
        return action
