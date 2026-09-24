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
import base64
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class EmployeeResignation(models.Model):
    """To create resignation request for the employee"""
    _name = 'employee.resignation'
    _description = 'Employee Resignation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'reference'

    reference = fields.Char(readonly=True, copy=False, default='New', string='Sequence', help='Reference for resignation')
    employee_id = fields.Many2one('hr.employee', help='To choose the employee')
    image_1920 = fields.Binary(related='employee_id.image_1920')
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    contract_id = fields.Many2one(domain="[('employee_id', '=', employee_id)]", readonly=False,
                                  related='employee_id.contract_id', help='Contract related to employee')
    department_id = fields.Many2one('hr.department',
                                    help='Select department for this employee',
                                    related='employee_id.department_id')
    joining_date = fields.Date(related='contract_id.date_start', help='Date of joining')
    end_date = fields.Date(related='contract_id.date_end', help='Contract end date')
    confirmed_date = fields.Date(help='The date when the resignation request, is confirmed by the employee itself')
    approved_date = fields.Date(help='The date when the resignation request, is approved by the manager')
    leaving_date = fields.Date(help='The date when the employee leaving after the notice period',
                               compute='_compute_leaving_date', store=True)
    notice_period = fields.Integer(help='Notice period of the employee, in days')
    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirmed'), ('waiting', 'Waiting'),
                              ('approved', 'Approved'), ('cancel', 'Rejected')], string='Status', default='draft',
                             track_visibility="always")
    resignation_type_id = fields.Many2one('resigned.reasons',
                                          help="Select the type of resignation", required=True)
    reason = fields.Text(string='Reason In Detail', help='To add the reason of the resignation in detail', required=True)
    total_working_years = fields.Float(string='Total Years Worked', readonly=True, help="Total working years")
    leave_taken = fields.Float(string='Training Period(Years)', readonly=True, help="Employee training years")
    gratuity_years = fields.Float(string='Gratuity Calculation Years', readonly=True, help="Employee gratuity years")
    basic_salary = fields.Float(readonly=True, help="Employee's basic salary.")
    gratuity_amount = fields.Float(readonly=True, help='Amount of appreciation payed to employee')
    gratuity_settlement_id = fields.Many2one('gratuity.settlement',
                                             help='Relation to the gratuity settlement')

    @api.depends('confirmed_date', 'notice_period')
    def _compute_leaving_date(self):
        """The function is used to confirm the leaving date after approving the request"""
        for rec in self:
            if rec.approved_date and rec.notice_period:
                approved_date = fields.Date.from_string(rec.approved_date)
                leaving_date = approved_date + timedelta(days=rec.notice_period)
                rec.leaving_date = fields.Date.to_string(leaving_date)
            else:
                rec.leaving_date = False

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        """Check for existing active requests when the employee is changed and
        to check the employee has the permission to create resignation request
        for another employee"""
        if self.employee_id:
            existing_requests = self.search([('employee_id', '=', self.employee_id.id),
                                             ('state', 'in', ['confirm', 'approved'])])
            if existing_requests and not self.env.user.has_group(
                    'cyllo_payroll_management.group_cyllo_payroll_management_manager'):
                raise ValidationError(
                    _('There is already an active or approved resignation request for this employee'))
            if not self.env.user.has_group(
                    'cyllo_payroll_management.group_cyllo_payroll_management_manager') and self.employee_id.user_id.id != self.env.uid:
                raise ValidationError(
                    _('You cannot create a request for other employees'))

    @api.model
    def create(self, vals):
        """Supering create function to add reference"""
        if vals.get('reference', 'New') == 'New':
            vals['reference'] = self.env['ir.sequence'].next_by_code('employee.resignation') or 'New'
        return super(EmployeeResignation, self).create(vals)

    def action_confirm_request(self):
        """The function is used to confirm the request"""
        return {
            'name': 'Confirm Resignation Request',
            'type': 'ir.actions.act_window',
            'res_model': 'resignation.request.confirm',
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'new',
            'context': {'default_reference': self.reference,
                        'default_employee_id': self.employee_id.id,
                        'default_department_id': self.department_id.id},
        }

    def action_cancel_request(self):
        """The function is used to cancel the request"""
        self.write({'state': 'cancel'})
        self.employee_id.is_resigned = False

    def action_approve_request(self):
        """The function is used to approve the request"""
        gratuity_details = self.env['gratuity.settlement'].sudo().search([('employee_id', '=', self.employee_id.id)],
                                                                         limit=1)
        if self.employee_id:
            self.employee_id.is_resigned = True
        for rec in self:
            rec.write({
                'state': 'approved',
                'approved_date': fields.date.today(),
                'leaving_date': fields.date.today() + timedelta(days=rec.notice_period)
            })
            for gratuity in gratuity_details:
                rec.write({
                    'gratuity_settlement_id': gratuity.id,
                    'leave_taken': gratuity.leave_taken,
                    'total_working_years': gratuity.total_working_years,
                    'basic_salary': gratuity.basic_salary,
                    'gratuity_years': gratuity.gratuity_years,
                    'gratuity_amount': gratuity.gratuity_amount
                })

    def action_reject_request(self):
        """The function is used to reject the request"""
        self.write({'state': 'cancel'})
        self.employee_id.is_resigned = False

    def action_reset_to_draft(self):
        """The function is used set the request in draft state"""
        self.write({'state': 'draft',
                    'approved_date': False,
                    'leaving_date': False,
                    'confirmed_date': False})
        self.employee_id.is_resigned = False

    def action_send_mail(self):
        """To send the resignation request to the department
        manager and the employee's direct manager"""
        resignation_report_template_id = self.env['ir.actions.report']._render_qweb_pdf(
            report_ref='cyllo_payroll_management.report_resignation_request', data=None, res_ids=self.ids)
        data_record = base64.b64encode(resignation_report_template_id[0])
        ir_values = {
            'name': "Resignation Request",
            'type': 'binary',
            'datas': data_record,
            'store_fname': data_record,
            'mimetype': 'application/pdf',
        }
        data_id = self.env['ir.attachment'].create(ir_values)
        template_id = self.env.ref('cyllo_payroll_management.mail_template_resignation_request')
        template_id.attachment_ids = [fields.Command.set([data_id.id])]
        department_manager = self.get_employee_partner(self.department_id.manager_id)
        employee_manager = self.get_employee_partner(self.employee_id)
        if not department_manager or not employee_manager:
            raise ValidationError(_("You can't send the mail because either "
                                    "the department manager or employee manager is missing."))
        else:
            for rec in self:
                rec.write({'state': 'waiting'})
            email_values = {
                'recipient_ids': [fields.Command.link(department_manager.id), fields.Command.link(employee_manager.id)],
                'email_from': self.employee_id.work_email
            }
            self.env['mail.template'].browse(template_id.id).send_mail(self.id, email_values=email_values,
                                                                       force_send=True)
            template_id.attachment_ids = [fields.Command.unlink(data_id.id)]

    def get_employee_partner(self, employee_id):
        """This method returns the contact for the given employee and if no
        contact found, the same method will be called with employee manager"""
        if employee_id.user_id:
            return employee_id.user_id.partner_id
        else:
            if employee_id.parent_id:
                return self.get_employee_partner(employee_id.parent_id)
            else:
                raise ValidationError("You can't send the mail because Employee/Department has no user and manager")
