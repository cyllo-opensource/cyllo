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


class GratuitySettlement(models.Model):
    """To create gratuity settlement of the employee"""
    _name = 'gratuity.settlement'
    _description = 'Gratuity Configuration'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'reference'

    reference = fields.Char(copy=False, readonly=True, default=lambda self: _('New'), help='Reference of the record')
    employee_id = fields.Many2one('hr.employee', required=True, help='Employee for gratuity settlement')
    contract_id = fields.Many2one("hr.contract", readonly=True, help="Latest employee contract")
    company_id = fields.Many2one('res.company', 'Company', required=True, help="Company",
                                 index=True, default=lambda self: self.env.company)
    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirmed'),
                              ('paid', 'Paid'), ('cancel', 'Cancelled')], default='draft', tracking=True)
    contract_type = fields.Selection([('limited', 'Limited'), ('open', 'Open')], readonly=True,
                                     help="If the contract have the end date then the contract type is limited, "
                                          "if the contract have not the end date the contract type will be unlimited",
                                     compute="_compute_contract_type", search="_search_contract_type")
    wage_type = fields.Selection([('monthly', 'Monthly Fixed Wage'), ('hourly', 'Hourly Wage')],
                                 help="Select the wage type monthly or hourly")
    total_working_years = fields.Float(string='Total Years Worked', help="Total working years",
                                       compute="_compute_gratuity_years")
    leave_taken = fields.Float(string='Training Period(Years)', help="Employee training years",
                               compute="_compute_gratuity_years")
    gratuity_years = fields.Float(string='Gratuity Calculation Years', help="Employee gratuity years",
                                  compute="_compute_gratuity_years")
    basic_salary = fields.Monetary(help="Employee's basic salary.", related="contract_id.wage")
    gratuity_configuration_id = fields.Many2one('gratuity.configuration', required=True,
                                                help="Gratuity configuration available for selected employee and contract type")
    gratuity_configuration_ids = fields.Many2many('gratuity.configuration',
                                                  compute="_compute_gratuity_configuration_ids",
                                                  help="Gratuity configuration available for selected employee and contract type")
    gratuity_duration_line_id = fields.Many2one('gratuity.configuration.line',
                                                string='Configuration Line', required=True,
                                                help="Gratuity configuration lines applicable for selected employee and contract type")
    gratuity_duration_line_ids = fields.Many2many('gratuity.configuration.line',
                                                  compute="_compute_gratuity_duration_line_ids",
                                                  help="Gratuity configuration lines applicable for selected employee and contract type")
    gratuity_amount = fields.Monetary(string='Gratuity Payment', readonly=True,
                                      help="It is calculated from "
                                           "(Employee basic salary * Extra allowed days *  Experience in years * Percentage) / "
                                           "(Divide in days * 100), where the values will be taken from gratuity configuration",
                                      compute="_compute_gratuity_amount")
    extra_days = fields.Integer(string="Extra days", help='Extra no. of days allowed for employee',
                                related="gratuity_duration_line_id.extra_days")
    percentage = fields.Float(string='Percentage', help='percentage of gratuity',
                              related="gratuity_duration_line_id.percentage")
    divide_days = fields.Integer(string='Divide days',
                                 help='This number of days will be divided with employee basic salary',
                                 related="gratuity_duration_line_id.divide_days")
    currency_id = fields.Many2one(related="company_id.currency_id", help="To get the Currency")

    @api.depends('contract_id', 'employee_id')
    def _compute_contract_type(self):
        """Get gratuity type based on employee contract"""
        contract_type = False
        for rec in self:
            if rec.contract_id:
                contract_type = 'limited' if rec.contract_id.date_end else 'open'
            rec.contract_type = contract_type

    @api.depends('gratuity_configuration_id')
    def _compute_gratuity_years(self):
        for rec in self:
            if rec.gratuity_configuration_id:
                total_days = 0
                gratuity_days = 0
                training_days = 0
                contracts = self.env['hr.contract'].sudo().search([
                    ('employee_id', '=', rec.employee_id.id),
                    ('state', 'not in', ('draft', 'cancel'))], order='date_start')
                if rec.contract_id and rec.employee_id and contracts:
                    config = rec.gratuity_configuration_id
                    if config.date_from == 'first':
                        total_days = (fields.Date.today() - contracts[0].date_start).days
                    elif config.date_from == 'current':
                        total_days = (fields.Date.today() - rec.contract_id.date_start).days
                    elif config.date_from == 'manual':
                        total_days = (fields.Date.today() - rec.gratuity_configuration_id.joining_date).days
                    elif config.date_from == 'exact':
                        for contract in contracts:
                            if not contract.date_start or not contract.date_end and contract != rec.contract_id:
                                raise ValidationError(
                                    _("To calculate exact experience of employee, all the contracts should have the start date and end date"))
                            elif contract != rec.contract_id:
                                total_days += (contract.date_end - contract.date_start).days
                            else:
                                total_days += (fields.Date.today() - contract.date_start).days

                    training_period = self.env['employee.training.period'].search(
                        [('employee_id', '=', rec.employee_id.id)])
                    for training in training_period:
                        start_date = training.start_date
                        end_date = training.end_date
                        training_days += (end_date - start_date).days
                    if rec.gratuity_configuration_id.include_training:
                        gratuity_days = total_days
                    else:
                        gratuity_days = total_days - training_days
                rec.write({
                    'gratuity_years': (gratuity_days / 365) if gratuity_days > 0 else 0,
                    'total_working_years': (total_days / 365) if total_days > 0 else 0,
                    'leave_taken': (training_days / 365) if training_days > 0 else 0
                })
            else:
                rec.write({
                    'gratuity_years': 0,
                    'total_working_years': 0,
                    'leave_taken': 0
                })

    @api.depends('employee_id', 'contract_type', 'contract_id')
    def _compute_gratuity_configuration_ids(self):
        """Get filtered gratuity configuration to provide domain for selecting gratuity configuration"""
        configurations = False
        for rec in self:
            if rec.employee_id:
                configurations = self.env['gratuity.configuration'].search([
                    ('contract_type', '=', rec.contract_type), '|',
                    ('end_date', '>=', fields.date.today()),
                    ('end_date', '=', False), '|',
                    ('start_date', '<=', fields.date.today()),
                    ('start_date', '=', False)])
            rec.gratuity_configuration_ids = configurations.ids if configurations else False

    @api.depends('gratuity_configuration_id', 'employee_id')
    def _compute_gratuity_duration_line_ids(self):
        """Get filtered gratuity configuration lines for selected employee and gratuity configuration"""
        lines = self.env['gratuity.configuration.line']
        for rec in self:
            line_ids = rec.gratuity_configuration_id.gratuity_configuration_ids
            for line in line_ids:
                if (line.from_year and line.to_year and line.from_year <=
                        rec.total_working_years <= line.to_year):
                    lines += line
                elif line.from_year and not line.to_year and line.from_year <= rec.total_working_years:
                    lines += line
                elif line.to_year and not line.from_year and rec.total_working_years <= line.to_year:
                    lines += line
                elif line.to_year == 0 and line.from_year == 0:
                    lines += line
            rec.gratuity_duration_line_ids = lines.ids if lines else False

    @api.depends('gratuity_configuration_id', 'contract_id', 'employee_id', 'gratuity_years', 'total_working_years',
                 'leave_taken', 'gratuity_duration_line_id')
    def _compute_gratuity_amount(self):
        """Compute total gratuity settlement amount for the selected configurations"""
        total_amount = 0
        for rec in self:
            if rec.gratuity_years > 0 and rec.employee_id and rec.gratuity_configuration_id and rec.gratuity_duration_line_id and rec.contract_id and rec.basic_salary:
                total_amount = (rec.basic_salary * rec.extra_days * rec.gratuity_years * rec.percentage) / (
                        rec.divide_days * 100)
            rec.gratuity_amount = total_amount if total_amount > 0 else 0

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        """Update employee related data when the employee is changed"""
        vals = {
            'contract_type': False,
            'contract_id': False,
            'gratuity_configuration_id': False,
            'gratuity_duration_line_id': False,
            'total_working_years': False,
            'gratuity_years': False,
            'leave_taken': False
        }
        if self.employee_id:
            self.write(vals)
            latest_contract = self.env['hr.contract'].sudo().search(
                [('employee_id', '=', self.employee_id.id),
                 ('state', '=', 'open')])
            if latest_contract:
                self.write({
                    'contract_id': latest_contract.id,
                })
            else:
                raise ValidationError(_("No running contract found for selected employee"))
        else:
            self.write(vals)

    @api.onchange('gratuity_configuration_id')
    def _onchange_gratuity_configuration_id(self):
        """Compute employee gratuity years based on selected gratuity configuration"""
        self.gratuity_duration_line_id = False

    @api.model
    def create(self, vals):
        """Supering create function to add reference"""
        if vals.get('reference', 'New') == 'New':
            vals['reference'] = self.env['ir.sequence'].next_by_code('gratuity.settlement') or 'New'
        return super(GratuitySettlement, self).create(vals)

    def action_confirm(self):
        """To submit the gratuity settlement"""
        self.write({'state': 'confirm'})

    def action_cancel(self):
        """To cancel the gratuity settlement"""
        self.write({'state': 'cancel'})

    def action_set_to_draft(self):
        """To reset gratuity settlement to draft state"""
        self.write({'state': 'draft'})

    def _search_contract_type(self, operator, value):
        settlements = self.env['gratuity.settlement'].search([])
        if operator == '=':
            filtered_settlements = settlements.filtered(lambda s: s.contract_type == value)
            return [('id', 'in', filtered_settlements.ids)]
        else:
            return [('id', 'in', settlements.ids)]
