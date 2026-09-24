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
from datetime import datetime


class SalaryCalculator(models.TransientModel):
    _name = 'salary.calculator'
    _description = 'Gross-Net Salary Calculator'

    # Inputs
    calculation_type = fields.Selection([
        ('manual', 'Manual'),
        ('employee', 'Employee'),
        ('department', 'Department')
    ], string="Calculation Type", default='manual')
    employee_id = fields.Many2one('hr.employee', string="Employee")
    department_id = fields.Many2one('hr.department', string="Department")
    struct_id = fields.Many2one('employee.salary.structure',
                                string="Salary Structure", required=True)
    work_schedule_id = fields.Many2one('resource.calendar',
                                       string="Working Schedule")

    salary = fields.Monetary(string="Salary", currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', default=lambda
        self: self.env.company.currency_id)
    company_id = fields.Many2one('res.company',
                                 default=lambda self: self.env.company)

    # Computed Result Fields
    gross_month = fields.Monetary(compute="_compute_results")
    total_allowance = fields.Monetary(compute="_compute_results")
    deduction = fields.Monetary(compute="_compute_results")
    net_month = fields.Monetary(compute="_compute_results")
    cost_month = fields.Monetary(compute="_compute_results")
    cost_year = fields.Monetary(compute="_compute_results")
    line_ids = fields.One2many('salary.calculator.line', 'calculator_id',
                               string="Simulation Lines",
                               compute="_compute_results")

    wage_type = fields.Selection([
        ('monthly', 'Monthly Fixed Wage'),
        ('hourly', 'Hourly Wage')
    ], string="Wage Type", default='monthly')

    house_rent=fields.Monetary(string="HRA")
    travel_allowance=fields.Monetary(string="Travel Allowance")
    meal_allowance=fields.Monetary(string="Meal Allowance")

    @api.onchange('employee_id', 'calculation_type', 'wage_type')
    def _onchange_employee_id(self):
        if self.calculation_type == 'employee' and self.employee_id:
            contract = self.employee_id.contract_id
            if contract:
                if self.wage_type == 'hourly':
                    self.salary = contract.hourly_wage
                else:
                    self.salary = contract.wage
                self.struct_id = contract.employee_salary_structure_id
                self.work_schedule_id = contract.resource_calendar_id
            else:
                return {
                    'warning': {
                        'title': _("No Active Contract Found"),
                        'message': _(
                            "The selected employee %s does not have an active or valid contract. Please configure a contract first ") % self.employee_id.name
                    }
                }
        elif self.calculation_type != 'employee':
            self.employee_id = False
        if self.calculation_type != 'department':
            self.department_id = False

    @api.depends('salary', 'struct_id', 'employee_id', 'department_id',
                 'calculation_type','meal_allowance','travel_allowance','house_rent')
    def _compute_results(self):
        for rec in self:
            rec.gross_month = 0.0
            rec.total_allowance = 0.0
            rec.deduction = 0.0
            rec.net_month = 0.0
            rec.cost_month = 0.0
            rec.cost_year = 0.0
            rec.line_ids = [(5, 0, 0)]

            if not rec.struct_id:
                continue

            if rec.calculation_type == 'employee' and rec.employee_id:
                contract = rec.employee_id.contract_id
                if contract:
                    # Logic for Hourly Wage Calculation
                    if rec.wage_type == 'hourly':
                        start_date = fields.Date.today().replace(day=1)
                        end_date = fields.Date.today()
                        start_dt = datetime.combine(start_date,
                                                    datetime.min.time())
                        end_dt = datetime.combine(end_date, datetime.max.time())
                        work_hours = contract.resource_calendar_id.get_work_hours_count(
                            start_dt, end_dt)
                        hourly_pay = contract.hourly_wage * work_hours

                        # Create a temporary contract with calculated wage
                        contract = self.env['hr.contract'].new({
                            'name': contract.name,
                            'employee_id': contract.employee_id.id,
                            'wage': hourly_pay,
                            'employee_salary_structure_id': rec.struct_id.id,
                            'resource_calendar_id': contract.resource_calendar_id.id,
                            'company_id': rec.company_id.id,
                            'state': 'open',
                        })

                    payslip = self.env['employee.payslip'].new({
                        'employee_id': rec.employee_id.id,
                        'contract_id': contract.id,
                        'structure_id': rec.struct_id.id,
                        'company_id': rec.company_id.id,
                        'start_date': fields.Date.today().replace(day=1),
                        'to_date': fields.Date.today(),
                    })
                    payslip._onchange_employee_id()
                    line_values = payslip._get_payslip_lines([contract.id],
                                                             payslip)

                    gross = 0.0
                    total_allowance = 0.0
                    net = 0.0
                    deduction = 0.0
                    employer_costs = 0.0
                    lines = []

                    for line in line_values:
                        code = line.get('code')
                        category_id = line.get('category_id')
                        category = self.env[
                            'employee.salary.rule.category'].browse(category_id)
                        total = line.get('amount', 0.0) * line.get('quantity',
                                                                   1.0) * line.get(
                            'rate', 100.0) / 100.0

                        if code == 'GROSS':
                            gross = total
                        elif code == 'NET':
                            net = total
                        elif category.code == 'ALW':
                            total_allowance += total
                        elif category.code == 'DED':
                            deduction += total
                        elif category.code == 'COMP':
                            employer_costs += total

                        lines.append((0, 0, {
                            'name': line.get('name'),
                            'code': code,
                            'category_id': category_id,
                            'quantity': line.get('quantity'),
                            'rate': line.get('rate'),
                            'amount': line.get('amount'),
                            'total': total,
                        }))

                    rec.gross_month = gross
                    rec.total_allowance = total_allowance
                    rec.deduction = deduction
                    rec.net_month = net
                    rec.cost_month = gross + employer_costs
                    rec.cost_year = rec.cost_month * 12
                    rec.line_ids = lines

            elif rec.calculation_type == 'department' and rec.department_id:
                employees = self.env['hr.employee'].search(
                    [('department_id', '=', rec.department_id.id)])
                total_gross = 0.0
                total_alw = 0.0
                total_ded = 0.0
                total_net = 0.0
                total_comp = 0.0
                aggregated_lines = {}

                for employee in employees:
                    emp_contract = employee.contract_id
                    if not emp_contract:
                        continue

                    # Logic for Hourly Wage Calculation (Department)
                    if rec.wage_type == 'hourly':
                        start_date = fields.Date.today().replace(day=1)
                        end_date = fields.Date.today()
                        start_dt = datetime.combine(start_date,
                                                    datetime.min.time())
                        end_dt = datetime.combine(end_date, datetime.max.time())
                        work_hours = emp_contract.resource_calendar_id.get_work_hours_count(
                            start_dt, end_dt)
                        hourly_pay = emp_contract.hourly_wage * work_hours

                        # Create a temporary contract
                        emp_contract = self.env['hr.contract'].new({
                            'name': emp_contract.name,
                            'employee_id': employee.id,
                            'wage': hourly_pay,
                            'employee_salary_structure_id': rec.struct_id.id,
                            'resource_calendar_id': emp_contract.resource_calendar_id.id,
                            'company_id': rec.company_id.id,
                            'state': 'open',
                        })

                    temp_payslip = self.env['employee.payslip'].new({
                        'employee_id': employee.id,
                        'contract_id': emp_contract.id,
                        'structure_id': rec.struct_id.id,
                        'company_id': rec.company_id.id,
                        'start_date': fields.Date.today().replace(day=1),
                        'to_date': fields.Date.today(),
                    })
                    temp_payslip._onchange_employee_id()
                    line_values = temp_payslip._get_payslip_lines(
                        [emp_contract.id], temp_payslip)

                    for line in line_values:
                        code = line.get('code')
                        category_id = line.get('category_id')
                        category = self.env[
                            'employee.salary.rule.category'].browse(category_id)
                        total = line.get('amount', 0.0) * line.get('quantity',
                                                                   1.0) * line.get(
                            'rate', 100.0) / 100.0

                        if code == 'GROSS':
                            total_gross += total
                        elif code == 'NET':
                            total_net += total
                        elif category.code == 'ALW':
                            total_alw += total
                        elif category.code == 'DED':
                            total_ded += total
                        elif category.code == 'COMP':
                            total_comp += total

                        if code not in aggregated_lines:
                            aggregated_lines[code] = {
                                'name': line.get('name'),
                                'code': code,
                                'category_id': category_id,
                                'quantity': line.get('quantity'),
                                'rate': line.get('rate'),
                                'amount': line.get('amount'),
                                'total': 0.0,
                            }
                        aggregated_lines[code]['total'] += total
                rec.gross_month = total_gross
                rec.total_allowance = total_alw
                rec.deduction = total_ded
                rec.net_month = total_net
                rec.cost_month = total_gross + total_comp
                rec.cost_year = rec.cost_month * 12
                rec.line_ids = [(0, 0, vals) for vals in
                                aggregated_lines.values()]

            elif rec.calculation_type == 'manual' and rec.salary:
                simulation_env = self.env['hr.employee'].sudo().with_context(
                    salary_simulation=True, tracking_disable=True)
                temp_employee = simulation_env.new({
                    'name': 'Simulation Employee',
                    'company_id': rec.company_id.id,
                })
                # For manual, if hourly is selected, assume 'salary' input is hourly rate
                # and calculate total based on standard work hours?
                # User asked for "based on contract and working schedule", manual works without contract.
                # So for manual, we might keep it simple or assume monthly equivalent is entered.
                # Or, if hourly, we need working schedule.
                # The manual mode requires 'work_schedule_id' as input field (line 39-40).

                wage_val = rec.salary
                if rec.wage_type == 'hourly' and rec.work_schedule_id:
                    start_date = fields.Date.today().replace(day=1)

                    end_date = fields.Date.today()

                    start_dt = datetime.combine(start_date, datetime.min.time())

                    end_dt = datetime.combine(end_date, datetime.max.time())

                    work_hours = rec.work_schedule_id.get_work_hours_count(
                        start_dt, end_dt)

                    wage_val = rec.salary * work_hours

                temp_contract = self.env['hr.contract'].sudo().new({
                    'name': 'Simulation Contract',
                    'employee_id': temp_employee.id,
                    'wage': wage_val,
                    'employee_salary_structure_id': rec.struct_id.id,
                    'resource_calendar_id': rec.work_schedule_id.id,
                    'house_rent':rec.house_rent,
                    'travel_allowance':rec.travel_allowance,
                    'meal_allowance':rec.meal_allowance,
                    'company_id': rec.company_id.id,
                    'state': 'open',
                })

                temp_employee.contract_id = temp_contract

                payslip = self.env['employee.payslip'].new({
                    'employee_id': temp_employee.id,
                    'contract_id': temp_contract.id,
                    'structure_id': rec.struct_id.id,
                    'company_id': rec.company_id.id,
                    'start_date': fields.Date.today().replace(day=1),
                    'to_date': fields.Date.today(),
                })
                line_values = payslip._get_payslip_lines([temp_contract.id],
                                                         payslip)

                gross = 0.0
                total_allowance = 0.0
                deduction = 0.0
                net = 0.0
                employer_costs = 0.0
                lines = []

                for line in line_values:
                    code = line.get('code')
                    category_id = line.get('category_id')
                    category = self.env['employee.salary.rule.category'].browse(
                        category_id)
                    total = line.get('amount', 0.0) * line.get('quantity',
                                                               1.0) * line.get(
                        'rate', 100.0) / 100.0

                    if code == 'GROSS':
                        gross = total
                    elif code == 'NET':
                        net = total
                    elif category.code == 'ALW':
                        total_allowance += total
                    elif category.code == 'DED':
                        deduction += total
                    elif category.code == 'COMP':
                        employer_costs += total

                    lines.append((0, 0, {
                        'name': line.get('name'),
                        'code': code,
                        'category_id': category_id,
                        'quantity': line.get('quantity'),
                        'rate': line.get('rate'),
                        'amount': line.get('amount'),
                        'total': total,
                    }))

                rec.gross_month = gross
                rec.total_allowance = total_allowance
                rec.deduction = deduction
                rec.net_month = net
                rec.cost_month = gross + employer_costs
                rec.cost_year = rec.cost_month * 12


class SalaryCalculatorLine(models.TransientModel):
    _name = 'salary.calculator.line'
    _description = 'Salary Calculator Line'

    calculator_id = fields.Many2one('salary.calculator', string="Calculator")
    name = fields.Char(string="Description")
    code = fields.Char(string="Code")
    category_id = fields.Many2one('employee.salary.rule.category',
                                  string="Rule Category")
    quantity = fields.Float(string="Quantity")
    rate = fields.Float(string="Rate (%)")
    amount = fields.Float(string="Amount")
    total = fields.Float(string="Total")
