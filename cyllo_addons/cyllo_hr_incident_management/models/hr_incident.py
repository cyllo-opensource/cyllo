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
from odoo.exceptions import UserError, ValidationError


class HrIncident(models.Model):
    """Model for managing HR incidents.
        This model manages incidents reported within a company, including
        details such as the incident category, description, initiator,
        receptor, handler and stage of the incident."""
    _name = 'hr.incident'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _description = 'Incident'

    name = fields.Char(default='New', readonly=True)
    company_id = fields.Many2one('res.company', required=True,
                                 default=lambda self: self.env.company)
    date = fields.Datetime(string='Submitted Date', readonly=True)
    date_done = fields.Datetime(string='Completion Date', readonly=True)
    incident_category_id = fields.Many2one('hr.incident.category',
                                           help='Choose a category related to the Incident',
                                           required=True)
    incident_description = fields.Html(
        help='Write a description related to the Incident')
    incident_action_description = fields.Html(
        help='Write a description related to the Incident action')
    incident_initiator_id = fields.Many2one('hr.employee', required=True,
                                            default=lambda
                                                self: self.env.user.employee_id,
                                            help='Choose an Incident Initiator')
    incident_initiator_department_id = fields.Many2one('hr.department',
                                                       string="Department of Incident Initiator",
                                                       help='Choose an Incident Initiator department',
                                                       related='incident_initiator_id.department_id')
    incident_initiator_email = fields.Char(string="Incident Initiator's E-mail",
                                           related='incident_initiator_id.work_email',
                                           help='Incident Initiator email address')
    incident_initiator_phone = fields.Char(string="Incident Initiator's Phone",
                                           related='incident_initiator_id.mobile_phone',
                                           help='Incident Initiator phone number')
    incident_receptor_id = fields.Many2one('hr.employee',
                                           help='Choose the Incident Receptor',
                                           required=True,
                                           default=lambda
                                               self: self.env.user.employee_id.parent_id or self.env.
                                           user.employee_id.department_id.manager_id)
    incident_receptor_department_id = fields.Many2one('hr.department',
                                                      string="Department of Incident Receptor",
                                                      help='Choose the Incident Receptor department',
                                                      related='incident_receptor_id.department_id')
    incident_receptor_email = fields.Char(string="Incident Receptor's E-mail",
                                          help='Incident Receptor email address',
                                          related='incident_receptor_id.work_email')
    incident_receptor_phone = fields.Char(string="Incident Receptor's Phone",
                                          help='Incident Receptor phone number',
                                          related='incident_receptor_id.mobile_phone')
    incident_handler_id = fields.Many2one('hr.employee',
                                          help='Incident Handler Name')
    incident_handler_department_id = fields.Many2one('hr.department',
                                                     string="Department of Incident Handler",
                                                     help='Choose the Incident handler department',
                                                     related='incident_handler_id.department_id')
    incident_handler_email = fields.Char(string="Incident Handler's E-mail",
                                         related='incident_handler_id.work_email',
                                         help='Incident Handler Email Address')
    incident_handler_phone = fields.Char(string="Incident Handler's Phone",
                                         help='Incident Handler Phone Number',
                                         related='incident_handler_id.mobile_phone')
    is_submitted = fields.Boolean(
        help="For the visibility of the Submit button")
    is_hr_manager = fields.Boolean(string="Is Manager",
                                   compute='_compute_is_hr_manager',
                                   help="For setting the stage readonly for hr users")
    incident_stage = fields.Selection(
        [('new', 'New'), ('submitted', 'Submitted'), ('assigned', 'Assigned'),
         ('ongoing', 'Ongoing'), ('completed', 'Completed'),
         ('cancel', 'Canceled')],
        default='new', group_expand='_read_group_stage',
        help='Incident handler Stage',
        copy=False)
    current_user_employee_id = fields.Many2one('hr.employee',
                                               compute='_compute_is_hr_manager')

    @api.model
    def _read_group_stage(self, stages, domain, order):
        """For expanding all stages in Kanban view"""
        return {
            'new': 'New',
            'submitted': 'Submitted',
            'assigned': 'Assigned',
            'ongoing': 'Ongoing',
            'completed': 'Completed',
        }

    @api.depends('name')
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

    @api.onchange('incident_initiator_id')
    def _onchange_incident_initiator_id(self):
        """Onchange function for fetching the request handler details"""
        if self.incident_initiator_id:
            if self.incident_initiator_id.parent_id:
                self.write({
                               'incident_receptor_id': self.incident_initiator_id.parent_id.id})
            elif self.incident_initiator_id.department_id.manager_id:
                self.write({
                               'incident_receptor_id': self.incident_initiator_id.department_id.manager_id.id})
            else:
                raise ValidationError(
                    _("It seems that there are no managers identified either for the initiator or"
                      "within the initiator's department."))

    @api.ondelete(at_uninstall=False)
    def _unlink_except_posted(self):
        """Function to prevent deleting"""
        if not self._context.get('force_delete') and any(
                request.incident_stage != 'cancel' for request in self):
            raise UserError(
                _('You can delete it only after cancelling the request.'))

    def action_submit_incident_request(self):
        """
        Submits the incident request, updating its stage to 'submitted' and
        sending a notification email to the incident receptor if the current
         user is either the incident initiator or an HR manager.
        :return: If the current user is not authorized to submit the request,
         returns a client action displaying a warning notification.
        """
        if self.current_user_employee_id == self.incident_initiator_id or self.is_hr_manager:
            self.write({
                'name': self.env['ir.sequence'].next_by_code(
                    'hr.incident') or _('New'),
                'incident_stage': 'submitted',
                'date': fields.Datetime.now(),
                'is_submitted': True
            })
            mail_template = self.env.ref("cyllo_hr_incident_management."
                                         "mail_template_incident_receptor_notification_email")
            mail_template.with_context(
                email_to=self.incident_receptor_email).sudo().send_mail(
                res_id=self.id, force_send=True)
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Submit Request"),
                    'message': _(
                        "Only the initiator or administrator can submit this request."),
                    'sticky': False,
                    'type': 'warning',
                }
            }

    def action_assign_to_me(self):
        """
        Assigns the current user as the handler for the incident if the user
        is either the incident receptor or an HR manager. Sends a notification
         email to the assigned handler.
        :return: If the user is not authorized to assign a handler, returns a
         client action displaying a warning notification.
        """
        if self.current_user_employee_id == self.incident_receptor_id or self.is_hr_manager:
            self.incident_handler_id = self.env.user.employee_id
            self.write({'incident_stage': 'assigned'})
            mail_template = self.env.ref(
                "cyllo_hr_incident_management.mail_template_incident_handler_notification_email")
            mail_template.with_context(
                email_to=self.incident_handler_email).sudo().send_mail(
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

    def action_assign_handler(self):
        """
        Assigns a handler to the incident if the current user is either the
        incident receptor or an HR manager. Sends a notification email
        to the assigned handler.
        :return: If the current user is not authorized to assign a handler,
        returns a client action displaying a warning notification. If no
        handler is assigned to the incident, returns a client action
        prompting to assign an employee.
        """
        if (self.current_user_employee_id == self.incident_receptor_id or
                self.is_hr_manager):
            if self.incident_handler_id:
                self.write({'incident_stage': 'assigned'})
                mail_template = self.env.ref(
                    "cyllo_hr_incident_management.mail_template_incident_handler_notification_email")
                mail_template.sudo().send_mail(res_id=self.id, force_send=True)

            else:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _("Assign a Handler"),
                        'message': _(
                            "Please assign an employee to handle the request."),
                        'sticky': False,
                        'type': 'warning',
                    }
                }
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

    def action_start_incident_enquiry(self):
        """
        Moves the incident to the ongoing state and sends a notification
        email to the incident initiator if the current user is either the
        incident handler or an HR manager.
        :return: If the current user is not authorized to start the
        investigation, returns a client action displaying a warning
        notification.
        """
        if self.current_user_employee_id == self.incident_handler_id or self.is_hr_manager:
            if self.incident_handler_id:
                self.write({'incident_stage': 'ongoing', })
                mail_template = self.env.ref(
                    "cyllo_hr_incident_management.mail_template_incident_initiator_notification_email")
                mail_template.sudo().send_mail(self.id, force_send=True)

        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Start Investigation"),
                    'message': _(
                        "Only the handler or administrator can start the request."),
                    'sticky': False,
                    'type': 'warning',
                }
            }

    def action_mark_as_done(self):
        """
        Marks the incident as completed and sends a notification email to the
        incident receptor if the current user is either the incident handler
        or an HR manager.
        :return: If the current user is not authorized to mark the incident as
         done, returns a client action displaying a warning notification.
        """
        if self.current_user_employee_id == self.incident_handler_id or self.is_hr_manager:
            self.write({
                'incident_stage': 'completed',
                'date_done': fields.Datetime.now()
            })
            mail_template = self.env.ref(
                "cyllo_hr_incident_management.mail_template_incident_receptor_completed_notification_email_")
            mail_template.sudo().send_mail(res_id=self.id, force_send=True)
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Mark as Done"),
                    'message': _(
                        "Only the handler or administrator can mark as done."),
                    'sticky': False,
                    'type': 'warning',
                }
            }

    # portal.mixin override
    def _compute_access_url(self):
        """Override portal mixin show detailed view of each records"""
        super()._compute_access_url()
        for request in self:
            request.access_url = (
                f'/incident_management/details/request/{request.id}')

    # Assign name for report in the portal
    def _get_report_base_filename(self):
        """Assign name for portal pdf report"""
        self.ensure_one()
        return 'Incident Management - %s' % self.name

    def action_cancel(self):
        """
            Cancels the incident by updating its stage to 'cancel'.
            """
        if self.env.user.employee_id.id in (
                self.incident_initiator_id.id, self.incident_receptor_id.id,
                self.incident_handler_id.id) or self.is_hr_manager:
            self.write({
                'incident_stage': 'cancel'
            })
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Warning"),
                    'message': _("Your not allowed the request"),
                    'sticky': False,
                    'type': 'warning',
                }
            }

    def action_set_to_new(self):
        """
        Reset the incident by updating its stage to 'new'.
        """
        if self.env.user.employee_id.id in (
                self.incident_initiator_id.id, self.incident_receptor_id.id,
                self.incident_handler_id.id) or self.is_hr_manager:
            self.write({
                'incident_stage': 'new'
            })
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Warning"),
                    'message': _("Your not allowed the request"),
                    'sticky': False,
                    'type': 'warning',
                }
            }
