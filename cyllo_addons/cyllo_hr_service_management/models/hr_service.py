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


class HrService(models.Model):
    """Class for managing service requests related to employees and equipment maintenance."""
    _name = 'hr.service'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _description = "Service Request"

    service_request_type = fields.Selection(
        string='Request Type',
        selection=[('service', 'Service'), ('custody', 'Custody')],
        default='service',
        help="Type of service request: 'Service' or 'Custody'.")
    name = fields.Char(string='Request Number', readonly=True,
                       default=lambda self: _('New'), copy=False,
                       help="Unique identifier for the service request.")
    company_id = fields.Many2one('res.company', readonly=True,
                                 default=lambda self: self.env.company,
                                 help="Company associated with the service request.")
    date = fields.Datetime(string='Submitted Date', readonly=True,
                           help="Date when the service request was submitted.")
    return_date = fields.Datetime(readonly=True,
                                  help="Date when the service request is expected to be returned.")
    date_done = fields.Datetime(string='Completion Date', readonly=True,
                                help="Date when the service request is marked as completed.")
    employee_id = fields.Many2one('hr.employee', string="Service Requester",
                                  required=True,
                                  help="Employee making the service request.")
    employee_department_id = fields.Many2one(
        related='employee_id.department_id', string="Requester's Department",
        help="Department of the employee making the service request.")
    service_handler_id = fields.Many2one('hr.employee', required=True,
                                         help="Employee assigned to handle the service request.")
    service_handler_department_id = fields.Many2one(
        related='service_handler_id.department_id',
        string="Handler's Department",
        help="Department of the employee assigned to handle the service "
             "request.")
    service_executor_id = fields.Many2one('hr.employee',
                                          help="Employee assigned to execute the service request.")
    service_executor_department_id = fields.Many2one(
        related='service_executor_id.department_id',
        string="Executor's Department",
        help="Department of the employee assigned to execute the "
             "service request.")
    service_category_id = fields.Many2one('hr.service.category',
                                          help="Category of the service request.")
    equipment_id = fields.Many2one('maintenance.equipment',
                                   help="Equipment associated with the service request.")
    maintenance_type = fields.Selection(
        [('corrective', 'Corrective'), ('preventive', 'Preventive')],
        default="corrective",
        help="Type of maintenance: 'Corrective' or 'Preventive'.")
    maintenance_request_id = fields.Many2one('maintenance.request',
                                             help="Maintenance request linked to the service request.",
                                             readonly=True)
    is_equipment_required = fields.Boolean(
        related='service_category_id.require_maintenance_order',
        help="Indicates whether equipment maintenance order is required.")
    expected_return_date = fields.Datetime(
        help="Expected date when the service request is to be returned.")
    state = fields.Selection(
        selection=[('draft', 'Draft'), ('submit', 'Submitted'),
                   ('approved', 'Approved'),
                   ('assign', 'Assign'), ('returned', 'Returned'),
                   ('quality', 'Quality'),
                   ('ongoing', 'Ongoing'), ('done', 'Done'),
                   ('cancel', 'Cancel')],
        default='draft', help="Current state of the service request.")
    description = fields.Html(
        help="Detailed description of the service request.")
    is_hr_manager = fields.Boolean(string="Is Manager",
                                   compute='_compute_is_hr_manager')
    current_user_employee_id = fields.Many2one('hr.employee',
                                               compute='_compute_is_hr_manager')

    @api.depends('employee_id')
    def _compute_is_hr_manager(self):
        """Compute the value of is_hr_manager based on the current user's group.
            This method checks if the current user has the 'hr.group_hr_user'
            group.If the user has this group, is_hr_manager is set to True;
            otherwise, it is set to False."""
        for rec in self:
            rec.current_user_employee_id = rec.env.user.employee_id
            if self.env.user.has_group('hr.group_hr_manager'):
                rec.is_hr_manager = True
            else:
                rec.is_hr_manager = False

    def action_submit(self):
        """Function for submitting the request, also generates sequence for the request"""
        if self.service_request_type == 'service':
            self.write({
                'name': self.env['ir.sequence'].next_by_code(
                    'service.request') or _('New'),
                'date': fields.Datetime.now(),
                'state': 'submit'
            })
        else:
            self.write({
                'name': self.env['ir.sequence'].next_by_code(
                    'custody.request') or _('New'),
                'date': fields.Datetime.now(),
                'state': 'submit'
            })
        email_values = {'email_to': self.employee_id.work_email}
        email_values_handler = {'email_to': self.service_handler_id.work_email}
        mail_template = self.env.ref(
            'cyllo_hr_service_management.mail_template_request_submitted')
        mail_template_handler = self.env.ref(
            'cyllo_hr_service_management.mail_template_request_for_service')
        mail_template.send_mail(self.id, email_values=email_values,
                                force_send=True)
        mail_template_handler.send_mail(self.id,
                                        email_values=email_values_handler,
                                        force_send=True)
        self._message_log(body="Service Request have been submitted")

    def action_assign(self):
        """Function for assigning a service executor"""
        if self.service_executor_id:
            self.write({'state': 'assign'})
            email_values = {'email_to': self.service_executor_id.work_email}
            mail_template = self.env.ref(
                'cyllo_hr_service_management.mail_template_assigned_on_a_request')
            body = _(
                "Service request have been assigned to ") + self.service_executor_id.name
            self._message_log(body=body)
            mail_template.send_mail(self.id, email_values=email_values,
                                    force_send=True)
        else:
            raise ValidationError(
                _("There is no executor assigned for this request."))

    def action_start(self):
        """Function for start the execution of the service"""
        self.write({'state': 'ongoing'})
        if self.is_equipment_required:
            self._create_request()

    def action_done(self):
        """Function for marking the request as done"""
        email_values_handler = {'email_to': self.service_handler_id.work_email}
        mail_template_handler = self.env.ref(
            'cyllo_hr_service_management.mail_template_service_completed')
        mail_template_handler.send_mail(self.id,
                                        email_values=email_values_handler,
                                        force_send=True)
        email_values = {'email_to': self.employee_id.work_email}
        mail_template = self.env.ref(
            'cyllo_hr_service_management.mail_template_service_completed')
        mail_template.send_mail(self.id, email_values=email_values,
                                force_send=True)
        self._message_log(body="Service have been completed")
        self.write({'state': 'done', 'date_done': fields.Datetime.now()})

    def action_approve(self):
        """Function for marking the request as done"""
        self.equipment_id.write({'employee_id': self.employee_id.id})
        self.write({'state': 'approved', 'date_done': fields.Datetime.now()})

    def action_return(self):
        """Function for returning the equipment"""
        if self.expected_return_date and self.expected_return_date < fields.Datetime.today():
            return {
                "type": "ir.actions.act_window",
                "name": "Late Reason",
                "res_model": "late.return.reason",
                "views": [[False, "form"]],
                "target": "new",
                "context": {'default_service_request_id': self.id}
            }
        else:
            self.write({
                'state': 'quality',
                'return_date': fields.Datetime.today(),
            })
            email_values_handler = {
                'email_to': self.service_handler_id.work_email}
            mail_template_handler = self.env.ref(
                'cyllo_hr_service_management.mail_template_equipment_ready_to_return')
            mail_template_handler.send_mail(self.id,
                                            email_values=email_values_handler,
                                            force_send=True)
            self._message_log(body="Equipment have been ready to return")

    def action_cancel(self):
        """Function for cancelling the service request"""
        email_values = {'email_to': self.employee_id.work_email}
        email_values_handler = {'email_to': self.service_handler_id.work_email}
        mail_template = self.env.ref(
            'cyllo_hr_service_management.mail_template_request_cancelled')
        mail_template_handler = self.env.ref(
            'cyllo_hr_service_management.mail_template_request_cancelled')
        mail_template.send_mail(self.id, email_values=email_values,
                                force_send=True)
        mail_template_handler.send_mail(self.id,
                                        email_values=email_values_handler,
                                        force_send=True)
        self.write({'state': 'cancel'})
        self._message_log(body="Service request have been canceled")

    def action_approve_quality(self):
        """Function for approve quality the service request"""
        email_values = {'email_to': self.employee_id.work_email}
        mail_template = self.env.ref(
            'cyllo_hr_service_management.mail_template_equipment_returned')
        mail_template.send_mail(self.id, email_values=email_values,
                                force_send=True)
        self.equipment_id.write({'employee_id': False})
        self.write({'state': 'returned'})
        self._message_log(body="Equipment have been returned")

    def action_draft(self):
        """Function for marking the request to draft state"""
        self.write({'state': 'draft'})

    def action_assign_to_me(self):
        """
        Assigns the current user as the handler for the incident if the user
        is either the incident receptor or an HR manager. Sends a notification
         email to the assigned handler.
        :return: If the user is not authorized to assign a handler, returns a
         client action displaying a warning notification.
        """
        if self.current_user_employee_id == self.service_handler_id or self.is_hr_manager:
            self.service_executor_id = self.env.user.employee_id
            self.write({'state': 'assign'})
            mail_template = self.env.ref(
                "cyllo_hr_service_management.mail_template_assigned_on_a_request")
            mail_template.with_context(
                email_to=self.service_executor_id.work_email).sudo().send_mail(
                res_id=self.id, force_send=True)
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Assign Handler"),
                    'message': _(
                        "Only the receptor or administrator can assign the handler."),
                    'sticky': False,
                    'type': 'warning',
                }
            }

    def _create_request(self):
        """Function for creating maintenance requests for service requests"""
        values = {
            'name': self.name,
            'service_id': self.id,
            'employee_id': self.employee_id.id,
            'request_date': fields.Datetime.today(),
            'user_id': self.env.user.id,
            'equipment_id': self.equipment_id.id,
            'maintenance_type': self.maintenance_type,
        }
        maintenance_request = self.env['maintenance.request'].create(values)
        self.maintenance_request_id = maintenance_request.id

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        """function for computing the server handler"""
        if self.employee_id.parent_id:
            self.service_handler_id = self.employee_id.parent_id.id
        elif self.employee_id.department_id.manager_id:
            self.service_handler_id = self.employee_id.department_id.manager_id.id
        else:
            self.service_handler_id = False

    def _compute_access_url(self):
        """Override portal mixin show detailed view of each records"""
        super()._compute_access_url()
        for request in self:
            request.access_url = f'/service_management/details/request/{request.id}'

    def _get_report_base_filename(self):
        """Assign name for portal pdf report"""
        self.ensure_one()
        return 'Service Management - %s' % self.name
