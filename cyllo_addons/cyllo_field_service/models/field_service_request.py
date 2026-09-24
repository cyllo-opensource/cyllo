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
from datetime import date, datetime
from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

AVAILABLE_PRIORITIES = [
    ('a', 'Low'),
    ('b', 'Medium'),
    ('c', 'High'),
    ('d', 'Very High'),
]


class FieldServiceRequest(models.Model):
    """In this class, we are defining the fields required for the model field.service.request. """
    _name = "field.service.request"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _description = "Field Service Request"
    _order = "priority desc, create_date desc"

    name = fields.Char(string="Number", default=_('New'), readonly=True,
                       copy=False,
                       help="Sequence number of current request")
    partner_id = fields.Many2one("res.partner",
                                 help="The name of the customer who is making the request.",
                                 string="Customer")
    description = fields.Html(help="Description about the service request")
    user_id = fields.Many2one("res.users", default=lambda self: self.env.user,
                              help="Current user")
    priority = fields.Selection(AVAILABLE_PRIORITIES, default='a', tracking=1,
                                help="Priority of the service request")
    company_id = fields.Many2one("res.company", required=True,
                                 default=lambda self: self.env.company,
                                 help="Current company")

    skill_category_id = fields.Many2one("field.service.skill.category",
                                        string="Category", tracking=True,
                                        ondelete="restrict", required=False,
                                        help="Skill categories to represent skills needed to complete the request ")
    hr_skill_ids = fields.Many2many(related='skill_category_id.hr_skill_ids',
                                    help="Skill required to complete the task")
    service_checklist_ids = fields.One2many("field.service.checklist",
                                            'field_service_request_id',
                                            string="Checklist",
                                            help="Tasks to complete the request",
                                            tracking=1)
    service_employee_suggestion_ids = fields.One2many(
        "field.service.employee.suggestion",
        'field_service_request_id',
        string="Employees", help="Suggestion of employees")
    submit_date = fields.Datetime(string="Submitted Date",
                                  help="Date in which the request submitted ",copy=False)
    confirmation_date = fields.Datetime(string="Service Started On",
                                        help="Date in which the request confirmed",copy=False)
    date_deadline = fields.Datetime(string="Deadline", tracking=1,
                                    help="Date in which the request have to be completed",
                                    copy=False)
    date_assigned = fields.Datetime(string="Assigned On", tracking=1,
                                    help="Date in which the request is assigned",
                                    copy=False, readonly=True)
    state = fields.Selection(
        selection=[('draft', 'Draft'), ('submit', 'Submitted'),
                   ('assigned', 'Assigned'),
                   ('in_progress', 'In Progress'), ('completed', 'Completed'),
                   ('cancel', 'Cancelled')], default='draft', tracking=1,
        help="Status of current request", group_expand='_read_group_stage')
    field_service_worker_ids = fields.One2many('field.service.worker',
                                               'field_service_request_id',
                                               string="Workers",
                                               help="Workers selected for the task")
    create_user_avatar = fields.Binary(string="Author",
                                       related='create_uid.image_1920')
    move_ids = fields.Many2many('account.move', string="Invoices")
    ready_to_invoice = fields.Boolean(compute="_compute_ready_to_invoice",
                                      help="If the request ready to invoice it will be true")
    num_invoices = fields.Integer(string="Number of invoices",
                                  help="Number of invoices of the request")
    sale_order_id = fields.Many2one('sale.order', 'Sale Order Item',
                                    domain="([('partner_id', '=', partner_id), ('state', '=', 'sale')])",
                                    help="Choose sale order related to the field service")
    is_mark_as_done = fields.Boolean(compute="_compute_is_mark_as_done")
    is_manager = fields.Boolean(compute="_compute_is_manager")
    is_invoiced = fields.Boolean(default=False)
    is_overdue = fields.Boolean(string="Is Overdue")

    _sql_constraints = [
        ('check_date_assigned', 'CHECK(date_deadline >= date_assigned)',
         'The Deadline date cannot be earlier than the Assigning date.')
    ]

    @api.onchange('skill_category_id', 'hr_skill_ids')
    def _onchange_hr_skill_ids(self):
        """Keep selected workers aligned with the current required skills."""
        for request in self:
            if not request.hr_skill_ids:
                continue
            request.field_service_worker_ids = request.field_service_worker_ids.filtered(
                lambda worker: worker.employee_id
                and worker.employee_id.skill_ids & request.hr_skill_ids
            )

    def _compute_ready_to_invoice(self):
        """Function to compute the visibility of invoice button"""
        for fields_service in self:
            fields_service.num_invoices = len(fields_service.move_ids)
            if (sum(fields_service.service_checklist_ids.filtered_domain(
                    [('status', '=', 'completed')]).mapped(
                    'service_cost')) - sum(
                fields_service.move_ids.mapped('amount_residual'))) <= 0:
                fields_service.ready_to_invoice = False
            else:
                fields_service.ready_to_invoice = True

    def _compute_is_mark_as_done(self):
        """Function to compute the visibility of cancel button"""
        for fields_service in self:
            checklist = fields_service.service_checklist_ids.filtered_domain(
                [('required', '=', True)])
            fields_service.is_mark_as_done = True
            if any(obj.status == 'completed' for obj in checklist):
                fields_service.is_mark_as_done = True
            else:
                fields_service.is_mark_as_done = False

    def _compute_is_manager(self):
        """Function to compute the user is manager"""
        for rec in self:
            if self.env.user.has_group(
                    'cyllo_field_service.group_cyllo_field_service_manager'):
                rec.is_manager = True
            else:
                rec.is_manager = False

    # portal.mixin override
    def _compute_access_url(self):
        super()._compute_access_url()
        for request in self:
            request.access_url = f'/field_service_request/{request.id}'

    @api.onchange('skill_category_id')
    def _onchange_skill_category_id(self):
        """This function is used to fetch the categories, skills and checklist regarding the skill category to the
        request form"""
        checklist_commands = [fields.Command.clear()]
        if self.skill_category_id:
            for line in self.skill_category_id.service_checklist_ids:
                if not line.product_id:
                    continue
                checklist_commands.append(fields.Command.create({
                    'required': line.required,
                    'service_cost': line.service_cost,
                    'time_required': line.time_required,
                    'product_id': line.product_id.id,
                }))
        self.service_checklist_ids = checklist_commands

    @api.onchange( 'date_assigned', 'date_deadline')
    def _onchange_date_assigned(self):
        """
            Validates the deadline and assigned dates on change.

            This method is triggered automatically when the `date_deadline` or `date_assigned` fields are changed.
            It ensures that the deadline (`date_deadline`) is always later than the assigned date (`date_assigned`).
            If the deadline is earlier than the assigned date, it raises a `ValidationError` to prevent the user from
            setting an invalid deadline.

            Workflow:
            1. Check if both `date_deadline` and `date_assigned` are set.
            2. Compare the two dates and ensure that the deadline is not earlier than the assigned date.
            3. Raise a `ValidationError` if the deadline is earlier than the assigned date.

            Raises:
            - ValidationError: If the deadline is set to a date earlier than the assigned date,
              the method raises a `ValidationError` with an appropriate message to prompt the user to correct the date.

        """
        if self.date_deadline and self.date_assigned and self.date_deadline < self.date_assigned:
            raise ValidationError(
                _("Please choose a deadline that is later than the assigned date."))

    @api.ondelete(at_uninstall=False)
    def _unlink_except_posted(self):
        """Function to prevent deleting lines on posted entries"""
        if not self._context.get('force_delete') and any(
                request.state != 'draft' for request in self):
            raise UserError(_('You can delete requests in draft state only.'))

    @api.model_create_multi
    def create(self, vals_list):
        """Send email and post in chatter when creating a new field service request"""
        for vals in vals_list:
            if not vals.get('name') or vals['name'] == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('field.service.request') or _('New')
        res= super().create(vals_list)
        template = self.env.ref('cyllo_field_service.mail_template_field_service_request_creation')
        template.send_mail(res.id, force_send=True, email_values={'auto_delete': False})
        return res

    def action_submit(self):
        """ Generate a sequence for the field service request. This method computes sequence based on the code
        field.service.request."""
        self.write({
            'state': 'submit',
            'submit_date': datetime.now(),
        })

    def action_confirm(self):
        """This function is used for submitting the field service request"""
        self.write({'state': 'submit'})

    def action_fetch_suitable_workers(self):
        """In this function, we are going to fetch the workers based on the skills"""
        employees_added = []
        skill_ids = self.hr_skill_ids.ids
        employees = self.env['hr.employee'].search(
            [('skill_ids', 'in', skill_ids)])
        employee_ids_added_set = set(employees_added)
        new_employees = employees.filtered(
            lambda emp: emp.id not in employee_ids_added_set)
        if new_employees:
            for employee in new_employees:
                service_ids = []
                if employee.availability_status != 'available':
                    existing_services = self.env[
                        'field.service.worker'].search_read(
                        [('employee_id', '=', employee.id),
                         ('field_service_request_id.state', '=',
                          'in_progress' if employee.availability_status == 'not_available' else 'assigned' if employee.availability_status == 'reserved' else False)],
                        ['field_service_request_id'])
                    service_ids = [
                        item.get('field_service_request_id', False)[0] for item
                        in existing_services if
                        item.get('field_service_request_id', False)]
                existing_suggestion = self.env[
                    'field.service.employee.suggestion'].search([
                    ('employee_id', '=', employee.id),
                    ('field_service_request_id', '=', self.id)
                ])
                if existing_suggestion:
                    if employee.id in self.field_service_worker_ids.employee_id.ids:
                        added_to_workers = True
                    else:
                        added_to_workers = False
                    existing_suggestion.write({
                        'added_to_workers': added_to_workers,
                        'field_service_request_ids': [(6, 0, service_ids)]
                    })
                else:
                    self.env['field.service.employee.suggestion'].create({
                        'employee_id': employee.id,
                        'field_service_request_id': self.id,
                        'skill_ids': [(6, 0, employee.skill_ids.ids)],
                        'added_to_workers': False,
                        'field_service_request_ids': [(6, 0, service_ids)]
                    })
                employees_added.append(employee.id)
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'info',
                    'sticky': False,
                    'message': _(
                        "There are no employees who possess this skill")
                }
            }
        return {
            'name': 'Employee Suggestion',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree',
            'domain': [('field_service_request_id', '=', self.id)],
            'res_model': 'field.service.employee.suggestion',
            'target': 'new',
            'context': {
                'field_service_request_id': self.id,
                'hide_control_panel': True
            }
        }

    def action_assign_workers(self):
        """Function for sending notification to assigned workers, adding workers to the followers and  move request to
         assigned state."""
        if not self.skill_category_id:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Missing Skill Category"),
                    'message': _("Please Add Skill Category."),
                    'sticky': False,
                    'type': 'warning',
                }
            }
        if self.field_service_worker_ids:
            self.sudo().write(
                {'state': 'assigned', 'date_assigned': fields.datetime.now()})
            for worker in self.field_service_worker_ids:
                followers = self.message_follower_ids.mapped('partner_id.id')
                if worker.employee_id.work_contact_id.id not in followers:
                    self.message_follower_ids.create({
                        'res_id': self.id,
                        'res_model': 'field.service.request',
                        'partner_id': worker.employee_id.work_contact_id.id
                    })
                mail_template = self.env.ref(
                    'cyllo_field_service.mail_template_field_service_request')
                if worker.employee_id.work_email:
                    mail_template['email_to'] = worker.employee_id.work_email
                    mail_template.with_context(
                        {'name': worker.employee_id.name}).sudo().send_mail(
                        self.id, force_send=True)

        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Assign Workers"),
                    'message': _("Please select the workers."),
                    'sticky': False,
                    'type': 'warning',
                }
            }

    def action_draft(self):
        """Function for sending notification to assigned workers and move
        request to assigned state"""
        self.sudo().write({'state': 'draft'})

    def action_cancel(self):
        """Function to cancel the field service request"""
        self.state = 'cancel'

    def action_service_start(self):
        """
        Starts the service by updating its state to 'in progress'. This method checks if any workers are assigned to
         perform the service.It also ensures that the current user initiating the action is among the assigned workers.
         If conditions are met, the service state is updated to 'in progress' with the confirmation date set to the
         current datetime.
        Raises:
        UserError: If no workers are assigned or if the current user is not allowed to start the service.
        """
        workers = []
        for fs_service_worker_id in self.field_service_worker_ids:
            workers.append(fs_service_worker_id.employee_id.id)
        if not workers:
            raise UserError(
                _("No Workers where assigned to perform this service"))
        if (self.env.user.has_group(
                'cyllo_field_service.group_cyllo_field_service_manager') or self.env.user.id in
                self.field_service_worker_ids.mapped('employee_id.user_id.id')):
            self.sudo().write(
                {'state': 'in_progress', 'confirmation_date': datetime.today()})
        else:
            raise UserError(
                _("Only the workers or managers allowed to start the service"))

    def action_mark_as_done(self):
        """In this function, change the task to done if all checklist completed"""
        service_checklist_ids = self.service_checklist_ids.filtered(
            lambda x: x.required and x.status == 'pending')
        workers = self.field_service_worker_ids
        if service_checklist_ids:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _(
                        "There are still pending checklist items that require completion"),
                    'type': 'warning',
                }}
        else:
            self.sudo().write({'state': 'completed'})

    def action_create_invoice(self):
        """
        Creates an invoice based on the service data. This method creates an invoice with specific details like
        move type, partner, currency, and invoice date.If there is a linked sale order, it adds the invoice to
        the sale order's invoice_ids and creates invoice lines.If there is no linked sale order, it creates invoice
         lines directly.Finally, it sets the created invoice as a move_id on the current record and opens the created
          invoice in a new window.
        Returns:
            dict: Action dictionary to open the created invoice in a new window.
        """
        invoice = self.create_invoice()
        if invoice:
            self.is_invoiced = True
            return {
                'name': 'create_invoice',
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_id': invoice.id,
                'res_model': 'account.move',
                'target': 'current'
            }

    def action_invoices(self):
        """Function return invoice for the request """
        return {
            'name': 'Invoices',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'domain': [('id', 'in', self.move_ids.ids)]
        }

    @api.model
    def _read_group_stage(self, stages, domain, order):
        """For expanding all stages in Kanban view"""
        return {
            'draft': 'Draft',
            'submit': 'Submitted',
            'assigned': 'Assigned',
            'in_progress': 'In Progress',
            'completed': 'Completed',
        }

    def create_invoice(self):
        """
            Create an invoice for completed service checklists. If a sale order is linked, associates the invoice
             with the order. Generates invoice lines based on completed service checklists.
            :return: The created invoice.
            :rtype: account.move
            """

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'currency_id': self.company_id.id,
            'invoice_date': date.today(),
            'invoice_origin': self.name,
        })
        if self.sale_order_id:
            self.sale_order_id.invoice_ids = [fields.Command.link(invoice.id)]
            for checklist in self.service_checklist_ids:
                if checklist.status == 'completed':
                    self.env['account.move.line'].create({
                        'move_id': invoice.id,
                        'product_id': checklist.product_id.id,
                        'price_unit': checklist.service_cost,
                        'sale_line_ids': [fields.Command.create({
                            'order_id': self.sale_order_id.id,
                            'product_id': checklist.product_id.id,
                            'qty_delivered': 1,
                            'price_unit': checklist.service_cost
                        })]
                    })
        else:
            for checklist in self.service_checklist_ids:
                if checklist.status == 'completed':
                    self.env['account.move.line'].create({
                        'move_id': invoice.id,
                        'product_id': checklist.product_id.id,
                        'price_unit': checklist.service_cost,
                    })
        self.move_ids = [fields.Command.link(invoice.id)]
        return invoice

    def create_invoice_timesheet(self, total_hours, price_unit):
        """
            Create an invoice for timesheet entries.
            :param total_hours: Total hours to be invoiced.
            :param price_unit: Unit price for invoicing per hour.
            :return: The created invoice.
            :rtype: account.move
            """
        product = self.env.ref(
            'cyllo_field_service.product_product_field_service')
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'currency_id': self.company_id.id,
            'invoice_date': date.today(),
            'invoice_origin': self.name,
        })
        if self.sale_order_id:
            self.sale_order_id.invoice_ids = [fields.Command.link(invoice.id)]
            self.env['account.move.line'].create({
                'move_id': invoice.id,
                'product_id': product.id,
                'quantity': total_hours,
                'price_unit': price_unit,
                'sale_line_ids': [fields.Command.create({
                    'order_id': self.sale_order_id.id,
                    'product_id': product.id,
                    'price_unit': price_unit,
                    'qty_delivered': total_hours,
                    'product_uom_qty': total_hours,
                })]
            })
        else:
            self.env['account.move.line'].create({
                'move_id': invoice.id,
                'product_id': product.id,
                'quantity': total_hours,
                'price_unit': price_unit,
            })
        self.move_ids = [fields.Command.link(invoice.id)]
        return invoice

    def _get_report_base_filename(self):
        """Providing name for report in the portal"""
        self.ensure_one()
        return 'Field Service Request- %s' % self.name

    def run_deadline_reminder(self):
        """
            Sends a deadline reminder email to field service workers for assigned service requests.

            This method is designed to run periodically (e.g., via a scheduled action) to send reminder emails to
            employees whose assigned service requests are approaching the deadline. The number of days before the
            deadline when the reminder should be sent is configured via the system parameter
            `cyllo_field_service.deadline_reminder`.

            Workflow:
            1. Finds all service requests that are in the 'assigned' state and have a non-empty deadline date.
            2. Filters the service requests based on their `date_deadline` to check if the current date matches the
               reminder date (calculated as `date_deadline` minus the number of reminder days).
            3. For each qualifying service request, it sends an email to all workers (field_service_worker_ids)
               who have a valid work email, using a pre-defined email template.

            Note:
            - The email template `cyllo_field_service.mail_template_field_service_request_deadline` must exist.
            - The system parameter `cyllo_field_service.deadline_reminder` defines how many days before the deadline the
              reminder should be sent.
        """
        requests = self.env['field.service.request'].search(
            [('state', '=', 'assigned'), ('date_deadline', '!=', False)])
        deadline_reminder = self.env['ir.config_parameter'].get_param(
            'cyllo_field_service.deadline_reminder')
        for rec in requests.filtered(lambda r: r.date_deadline):
            reminder_date = rec.date_deadline.date() - relativedelta(
                days=int(deadline_reminder))
            if reminder_date == fields.Date.today():
                mail_template = self.env.ref(
                    'cyllo_field_service.mail_template_field_service_request_deadline')
                for worker in rec.field_service_worker_ids.filtered(
                        lambda w: w.employee_id.work_email):
                    mail_template.with_context({
                        'name': worker.employee_id.name,
                    }).sudo().send_mail(rec.id, email_values={
                        'email_to': worker.employee_id.work_email},
                                        force_send=True)
