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
from odoo import api, fields, models
from odoo.exceptions import UserError


class EmployeePayslipBatchList(models.Model):
    """The class is used to generate multiple payslip like batch based on the
    structure and the department"""
    _name = 'employee.payslip.batch.list'
    _description = 'Employee Payslip Batch List'

    batch_payslip_id = fields.Many2one('employee.payslip.batch', string='Payslip Reference',
                                       help="Select the payslip run to which this  is associated.")
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    employee_ids = fields.Many2many('hr.employee', 'hr_employee_group_rel', 'payslip_id',
                                    'employee_id', 'Employees', readonly=False,
                                    default=lambda self: self._get_employee_ids(), compute='_compute_employee_ids',
                                    store=True, help="Select the employees associated with this payslip.")
    department_id = fields.Many2one('hr.department',
                                    help='Set a specific department if you wish to select all the employees from this '
                                         'department (and sub departments) at once.')
    structure_id = fields.Many2one('employee.salary.structure', string='Salary Structure',
                                   help='Set a specific structure if you wish to make an extra payslip '
                                        '(eg: End of the year bonus). If you leave this field empty, a regular '
                                        'payslip will be generated for all the selected employees, based on their '
                                        'contracts configuration.')

    def _get_employee_ids(self):
        """ To return all employee records"""
        return self.env['hr.employee'].search([])

    @api.depends('department_id')
    def _compute_employee_ids(self):
        """ Compute the employees associated with this payslip based on the department."""
        for record in self.filtered(lambda x: x.department_id):
            employees = self.env['hr.employee'].search([('department_id', '=', record.department_id.id)])
            record.employee_ids = employees.ids

    def action_compute_sheet(self):
        """Generate payslips for selected employees."""
        global new_payslip
        [data] = self.read()
        active_id = self.env.context.get('active_id')

        if active_id:
            batch_data = self.env['employee.payslip.batch'].browse(active_id)
            from_date = batch_data.start_date
            to_date = batch_data.end_date
            batch_data.employee_payslip_ids.unlink()
        else:
            raise UserError("No active batch found.")

        if not data['employee_ids']:
            raise UserError("You must select employee(s) to generate payslip(s).")

        employees = self.employee_ids.filtered(
            lambda record: record.department_id == self.department_id) if self.department_id else self.employee_ids

        payslips = self.env['employee.payslip']
        for employee in employees:
            payslip_data = self.env['employee.payslip'].get_batch_payslips(from_date, to_date, employee.id,
                                                                           contract_id=False)
            contract_id = self.env['hr.contract'].browse(payslip_data['value'].get('contract_id'))
            res = {
                'employee_id': employee.id,
                'payslip_name': payslip_data['value'].get('payslip_name'),
                'structure_id': self.structure_id.id or payslip_data['value'].get('structure_id'),
                'contract_id': contract_id.id,
                'employee_payslip_batch_id': active_id,
                'employee_payslip_input_ids': [fields.Command.create(x) for x in payslip_data['value'].get(
                    'employee_payslip_input_ids')],
                'employee_worked_days_ids': [fields.Command.create(x) for x in payslip_data['value'].get(
                    'employee_worked_days_ids')],
                'start_date': from_date,
                'to_date': to_date,
                'company_id': employee.company_id.id,
                'journal_id': self.env.ref('cyllo_payroll_management.account_journal_salaries').id,
                'is_batch_payslip': True,
                'state': 'waiting',
                'batch_payslip_name': batch_data.name
            }
            if res['contract_id']:
                new_payslip = self.env['employee.payslip'].create(res)
                payslips += new_payslip
                if res['structure_id']:
                    payslips |= new_payslip
                for rec in payslips:
                    rec._onchange_employee_id()
                    rec.action_compute_sheet()
                    batch_data.write({'state': 'confirm'})
        return {'type': 'ir.actions.act_window_close'}
