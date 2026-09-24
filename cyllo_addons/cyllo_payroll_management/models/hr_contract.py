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
from datetime import timedelta, date

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.addons.hr_work_entry_holidays.models.hr_contract import HrContract


class PayrollHrContract(models.Model):
    """To create employee contract """
    _inherit = 'hr.contract'

    employee_salary_structure_id = fields.Many2one('employee.salary.structure', string='Salary Structure',
                                                   domain="[('country_id', '=', company_country_id),('type_id','=',structure_type_id)]",
                                                   help="To select salary structure applicable for this employee")
    yearly_wage = fields.Float(string='Yearly Cost', help='To get the yearly cost',
                               compute='_compute_yearly_wage', store=True)
    training_date_from = fields.Date(string='Training Start Date', help="Employee training period start date")
    training_date_to = fields.Date(string='Training End Date', help="Employee training period end date")
    wage_type = fields.Selection([('monthly', 'Monthly Fixed Wage'), ('hourly', 'Hourly Wage')])
    default_schedule_pay = fields.Selection(related='employee_salary_structure_id.schedule_pay',
                                            string='Scheduled Pay', index=True,
                                            help="Defines the frequency of the wage payment.")
    state = fields.Selection(selection_add=[('training', 'Training Period'), ('open',)])
    is_approved = fields.Boolean(default=False, help='To check the contract is approved or not')
    hourly_wage = fields.Monetary('Hourly Wage', digits=(16, 2), default=0, required=True, tracking=True,
                                  help="Employee's hourly gross wage.")
    trainee = fields.Boolean(string="Trainee", help="This employee can have a training period if this field is checked")
    house_rent = fields.Monetary(string='HRA', help="House rent allowance of the employee")
    travel_allowance = fields.Monetary(help="Travel allowance for the employee")
    dearness_allowance = fields.Monetary(help="The dearness allowance for the employee")
    meal_allowance = fields.Monetary(help="The meal allowance for the employees")
    medical_allowance = fields.Monetary(help="The medical allowance for the employees")
    other_allowance = fields.Monetary(help="The other allowance for employees")
    employee_training_period_id = fields.Many2one('employee.training.period', readonly=True,
                                                  help="Employee training period data")
    half_time_off_ids = fields.Many2many('hr.leave', help="Time off related to this employee")

    @api.depends('wage')
    def _compute_yearly_wage(self):
        """To calculate the yearly wage based on working days"""
        for contract in self.filtered(lambda x: x.wage):
            contract.yearly_wage = contract.wage * 12

    @api.constrains('training_date_from', 'training_date_to')
    def _check_training_date_order(self):
        """To Check the training dates are valid"""
        for record in self:
            if record.training_date_from > record.training_date_to:
                raise ValidationError("Training Start date must be before  Training end date.")

    @api.onchange('structure_type_id')
    def _onchange_structure_type_id(self):
        """This function is used to set the structure field to false while changing the structure type"""
        self.employee_salary_structure_id = False

    @api.model_create_multi
    def create(self, vals_list):
        """Function for create a record based on training details of an employee in a model"""
        for rec in vals_list:
            if rec.get('trainee'):
                training_details = self.env['employee.training.period'].sudo().create({
                    'employee_id': rec.get('employee_id'),
                    'start_date': rec.get('training_date_from'),
                    'end_date': rec.get('training_date_to'),
                })
                rec['employee_training_period_id'] = training_details.id
                rec['state'] = 'training'
        res = super(PayrollHrContract, self).create(vals_list)
        return res

    def get_all_structures(self):
        """ @return: the structures linked to the given contracts, ordered by hierarchy (parent=False first,then
        first level children and so on) and without duplicate"""
        structures = self.mapped('employee_salary_structure_id')
        if not structures:
            return []
        return list(set(structures._get_parent_structure().ids))

    def action_approve_contract(self):
        """The button is used to approve the contract after ending the training period,
        it will move to the open state, that means the contract is running"""
        for contract in self:
            if not contract.training_date_from or not contract.training_date_to:
                raise ValidationError(_("Please add the Training Start Date and End Date"))
            if contract.training_date_from and contract.training_date_to:
                contract.write({'is_approved': True})
                if contract.state == 'training':
                    contract.write({'state': 'open',
                                    'date_start': contract.training_date_to + timedelta(days=1),
                                    'date_end': False})
                contract.write({'state': 'open'})
                contract.employee_training_period_id.write({'state': 'done'})


def custom_write(self, vals):
    if vals.get('trainee'):
        training_details = self.env[
            'employee.training.period'].sudo().create({
            'employee_id': vals.get('employee_id') or self.employee_id.id,
            'start_date': vals.get('training_date_from') or self.training_date_from,
            'end_date': vals.get('training_date_to') or self.training_date_to,
        })
        vals['employee_training_period_id'] = training_details.id
        vals['state'] = 'training'

    # Special case when setting a contract as running:
    # If there is already a validated time off over another contract
    # with a different schedule, split the time off, before the
    # _check_contracts raises an issue.
    # If there are existing leaves that are spanned by this new
    # contract, update their resource calendar to the current one.
    if not (vals.get("state") == 'open' or vals.get('kanban_state') == 'done'):
        return super(HrContract, self).write(vals)
    specific_contracts = self.env['hr.contract']
    all_new_leave_origin = []
    all_new_leave_vals = []
    leaves_state = {}
    # In case a validation error is thrown due to holiday creation with the new resource calendar (which can
    # increase their duration), we catch this error to display a more meaningful error message.
    try:
        for contract in self:
            if vals.get('state') != 'open' and contract.state != 'draft':
                # In case the current contract is not in the draft state, the kanban_state transition does not
                # cause any leave changes.
                continue
            leaves = contract._get_leaves()
            for leave in leaves:
                # Get all overlapping contracts but exclude draft contracts that are not included in this transaction.
                overlapping_contracts = leave._get_overlapping_contracts(contract_states=[
                    ('state', '!=', 'cancel'),
                    ('resource_calendar_id', '!=', False),
                    '|', '|', ('id', 'in', self.ids),
                    ('state', '!=', 'draft'),
                    ('kanban_state', '=', 'done'),
                ]).sorted(key=lambda c: {'open': 1, 'close': 2, 'training': 3, 'draft': 4, 'cancel': 5}[c.state])
                if len(overlapping_contracts.resource_calendar_id) <= 1:
                    if overlapping_contracts and leave.resource_calendar_id != overlapping_contracts[
                        0].resource_calendar_id:
                        leave.resource_calendar_id = overlapping_contracts[0].resource_calendar_id
                    continue
                if leave.id not in leaves_state:
                    leaves_state[leave.id] = leave.state
                if leave.state != 'refuse':
                    leave.action_refuse()
                super(HrContract, contract).write(vals)
                specific_contracts += contract
                for overlapping_contract in overlapping_contracts:
                    new_request_date_from = max(leave.request_date_from, overlapping_contract.date_start)
                    new_request_date_to = min(leave.request_date_to, overlapping_contract.date_end or date.max)
                    new_leave_vals = leave.copy_data({
                        'request_date_from': new_request_date_from,
                        'request_date_to': new_request_date_to,
                        'state': leaves_state[leave.id],
                    })[0]
                    new_leave = self.env['hr.leave'].new(new_leave_vals)
                    new_leave._compute_date_from_to()
                    new_leave._compute_duration()
                    # Could happen for part-time contract, that time off is not necessary
                    # anymore.
                    if new_leave.date_from < new_leave.date_to:
                        all_new_leave_origin.append(leave)
                        all_new_leave_vals.append(new_leave._convert_to_write(new_leave._cache))
        if all_new_leave_vals:
            new_leaves = self.env['hr.leave'].with_context(
                tracking_disable=True,
                mail_activity_automation_skip=True,
                leave_fast_create=True,
                leave_skip_state_check=True
            ).create(all_new_leave_vals)
            new_leaves.filtered(lambda l: l.state in 'validate')._validate_leave_request()
            for index, new_leave in enumerate(new_leaves):
                new_leave.message_post_with_source(
                    'mail.message_origin_link',
                    render_values={'self': new_leave, 'origin': all_new_leave_origin[index]},
                    subtype_xmlid='mail.mt_note',
                )
    except ValidationError:
        raise ValidationError(_("Changing the contract on this employee changes their working schedule in a period "
                                "they already took leaves. Changing this working schedule changes the duration of "
                                "these leaves in such a way the employee no longer has the required allocation for "
                                "them. Please review these leaves and/or allocations before changing the contract."))
    return super(HrContract, self - specific_contracts).write(vals)

HrContract.write = custom_write
