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
from datetime import datetime, timedelta

from odoo import _, api, Command, fields, models
from odoo.exceptions import UserError


class SupportServiceTicket(models.Model):
    """ Class defines support service Ticket model"""
    _name = "support.service.ticket"
    _description = " Support Service Ticket"
    _rec_name = 'ticket'
    _primary_email = 'email_from'
    _inherit = ['mail.activity.mixin', 'rating.mixin', 'portal.mixin']

    ticket = fields.Char(string='Sequence Number', readonly=True,
                         default=lambda self: _('New'),
                         help="Support Service ticket Id", copy=False)
    fb_user_number = fields.Char(string='Unique Facebook Id',
                                 help="Unique identifier for the partner on Facebook.")
    name = fields.Char(required=True, help="Small description about the issue",
                       tracking=True)
    mail_message_id = fields.Many2one('mail.message',
                                      string='Related Mail Message',
                                      help="Message related to this lead")
    team_id = fields.Many2one('support.service.team',
                              help="Support Service Team",
                              string="Support Team", tracking=True)
    manager_id = fields.Many2one('res.users', related='team_id.manager_id')
    is_paid = fields.Boolean(string="Paid or Not", related="team_id.is_paid")
    priority = fields.Selection(
        selection=[('0', 'Normal'), ('1', 'Low'), ('2', 'High'),
                   ('3', 'Very High')],
        default='0')
    ticket_type = fields.Selection(
        selection=[('enquiries', 'Enquiries'), ('issues', 'Issues')],
        default='enquiries')
    customer_id = fields.Many2one('res.partner', tracking=True, required=True,
                                  help="Customer of the ticket")
    email = fields.Char(help="Customer email id")
    email_from = fields.Char(help="Customer Email")
    phone = fields.Char(related='customer_id.phone',
                        help="Customer phone number")
    category_id = fields.Many2one('support.service.category',
                                  ondelete='restrict', help="Ticket category")
    tag_ids = fields.Many2many('support.service.tag', help="Ticket tags",
                               ondelete='restrict')
    user_id = fields.Many2one('res.users', string="Assigned to",
                              tracking=True,
                              help="The person to whom the ticket assigned to")
    company_id = fields.Many2one('res.company', required=False,
                                 default=lambda self: self.env.company,
                                 help="Company for the support service ticket")
    description = fields.Html(help="Description about the issue or question")
    timesheet_ids = fields.One2many('account.analytic.line', 'ticket_id',
                                    string="Timesheet Details", tracking=True,
                                    help="Time spent by the employee for this ticket")
    is_timesheet = fields.Boolean(string="Timesheet",
                                  related='team_id.is_timesheet')
    timesheet_time = fields.Float()
    timer_toggle = fields.Boolean(string="Time Toggle")
    is_failed = fields.Boolean(string="Failed ticket", default=False,
                               help="Ticket that failed to finish within deadline",
                               compute="_compute_is_failed", store=True)
    activity_ids = fields.One2many('mail.activity')
    stage_id = fields.Many2one('support.service.stage', string="Status",
                               default=lambda self: self.env.ref(
                                   'cyllo_support_service.support_service_stage_new').id,
                               copy=False, tracking=True,
                               group_expand='_expand_states',
                               ondelete="restrict",
                               help="Support Service stages")
    stage_change_date = fields.Datetime(compute="_compute_stage_change_date")
    stage_name = fields.Char(string="Stage", related='stage_id.name')
    sequence = fields.Integer(related='stage_id.sequence',
                              help="Stage sequence number")
    date = fields.Datetime(default=datetime.now(), tracking=True)
    deadline = fields.Datetime(tracking=True, default=datetime.now(),
                               help="Within this date the work need to finish")
    closed_date = fields.Datetime(compute='_compute_closed_date', store=True)
    last_seven_days = fields.Datetime(string="Closed Last 7 Days",
                                      compute="_compute_last_seven_days")
    sale_order_item_id = fields.Many2one(
        'sale.order',
        help="Choose the sale order item in which the time spent on this ticket will be added to invoice")
    is_closed_today = fields.Boolean(string='Closed Today', store=True,
                                     compute='_compute_is_closed_today')
    create_user_avatar = fields.Binary(string="Author",
                                       related='create_uid.image_1920')
    is_sale_order = fields.Boolean(string="Sale order",
                                   help="Boolean to check sale oder created or not")
    ticket_sale_order = fields.Integer(string="Sale Order Id")
    ticket_order_id = fields.Many2one('sale.order', string="Sale Order")
    ticket_invoice_ids = fields.Many2many('account.move', string="Invoice Id")
    service_task_id = fields.Many2one('project.task',
                                      string='Field service task')
    is_invoice_status = fields.Boolean(compute="_compute_is_invoice_status",
                                       string="Invoice",
                                       help="Boolean to check invoice created or not")
    invoice_count = fields.Integer(compute="_compute_invoice_count",
                                   help="Field to show the count of invoice")
    sale_order_count = fields.Integer(compute="_compute_sale_order_count",
                                      help="Field to show the count of sale order")
    is_repair_order = fields.Boolean(compute="_compute_is_repair_order",
                                     string="Repair Order",
                                     help="Boolean to check repair order created or not")
    repair_count = fields.Integer(compute="_compute_repair_count",
                                  help="Field to show the count of repair order")
    is_task = fields.Boolean(compute="_compute_is_task", string="Project Task",
                             help="Boolean to check task created or not")
    task_count = fields.Integer(compute="_compute_task_count",
                                help="Field to show the count of task")
    ticket_source = fields.Selection(string="Source", readonly=True,
                                     help="This is the source of the ticket.",
                                     selection=[('email', 'Gmail'),
                                                ('facebook', 'Facebook'),
                                                ('portal', 'Customer Portal')])
    type_of_issue = fields.Selection(selection=[('refund', 'Refund'),
                                                ('repair', 'Repair'),
                                                ('field', 'Field Service')],
                                     string="Type of Issue", default="refund")

    @api.depends('deadline', 'stage_id.is_closed')
    def _compute_is_failed(self):
        """Function to mark tickets as failed if past deadline and not closed."""
        today = fields.Datetime.now()
        for ticket in self:
            if (
                    ticket.deadline
                    and not ticket.stage_id.is_closed
                    and not ticket.stage_id.is_canceled
                    and ticket.deadline < today
            ):
                ticket.is_failed = True
            else:
                ticket.is_failed = False

    @api.depends('stage_id')
    def _compute_stage_change_date(self):
        """ Function to calculate ticket change date for inactivity """
        for rec in self:
            rec.stage_change_date = fields.datetime.today()

    @api.depends('stage_id')
    def _compute_closed_date(self):
        """ Function to calculate ticket closing date """
        for rec in self:
            rec.closed_date = fields.datetime.today() if rec.stage_id.is_closed else ''

    def _compute_last_seven_days(self):
        """ Function to calculate last seven days """
        for rec in self:
            rec.last_seven_days = datetime.now() - timedelta(days=6)

    @api.depends('closed_date')
    def _compute_is_closed_today(self):
        """ Function that finds ticket closed today """
        for record in self:
            record.is_closed_today = fields.Date.to_date(
                record.closed_date) == fields.Date.today()

    def _compute_is_invoice_status(self):
        """ Function to compute invoice status """
        for rec in self:
            rec.is_invoice_status = False
            if rec.ticket_order_id:
                rec.is_invoice_status = (
                        rec.ticket_order_id and rec.ticket_order_id.invoice_status
                        not in ['no', 'to invoice'])
            elif rec.ticket_invoice_ids:
                rec.is_invoice_status = True

    def _compute_invoice_count(self):
        """
        Compute and set the number of related invoices for the current ticket.

        This method searches for invoices in the 'account.move' model based on the
        'ticket_invoice_ids' and updates the 'invoice_count' field accordingly.

        :return: None
        """
        for rec in self:
            rec.invoice_count = 1 if self.ticket_invoice_ids else 0

    def _compute_is_repair_order(self):
        """ Function to compute repair status """
        for rec in self:
            rec.is_repair_order = False
            repair = self.env['repair.order'].sudo().search(
                [('ticket_id', '=', rec.id)])
            if repair:
                rec.is_repair_order = True

    def _compute_repair_count(self):
        """
        Compute and set the number of related repair orders for the current ticket.

        This method searches for repair orders in the 'repair.order' model based on the
        'ticket_id' and updates the 'repair_count' field accordingly.

        :return: None
        """
        for rec in self:
            rec.repair_count = self.env['repair.order'].search_count(
                [('ticket_id', '=', rec.id)])

    def _compute_is_task(self):
        """ Function to compute task status """
        for rec in self:
            rec.is_task = False
            if rec.service_task_id:
                rec.is_task = True

    def _compute_task_count(self):
        """
        Compute and set the number of related tasks for the current ticket.

        This method searches for tasks in the 'project.task' model based on the
        'ticket_id' and updates the 'task_count' field accordingly.

        :return: None
        """
        for rec in self:
            rec.task_count = self.env['project.task'].search_count(
                [('ticket_id', '=', rec.id)])

    def _compute_sale_order_count(self):
        """
        Compute and set the number of related sale orders for the current ticket.

        This method searches for sale orders in the 'sale.order' model based on the
        'ticket_reference' and updates the 'sale_order_count' field accordingly.

        :return: None
        """
        for rec in self:
            rec.sale_order_count = self.env['sale.order'].search_count(
                [('ticket_reference', '=', rec.id)])

    # portal.mixin override
    def _compute_access_url(self):
        super()._compute_access_url()
        for request in self:
            request.access_url = f'/support-service-ticket/{request.id}'

    @api.constrains('type_of_issue')
    def _check_type_of_issue(self):
        """
        Create a service task related to the current ticket if it is marked as a field service.

        This constraint is triggered when the 'type_of_issue' field is updated. If 'type_of_issue'
        is 'field' and 'service_task_id' is not set, it searches for an existing 'Field Service' project.
        If not found, it creates a new project. Then, it creates a new service task linked to the ticket
        through the 'ticket_id' field.

        :return: None
        """
        if self.type_of_issue == "field" and not self.service_task_id:
            service_project_id = self.env['project.project'].sudo().search(
                [('name', '=', 'Field Service')])
            if not service_project_id:
                service_project_id = self.env['project.project'].create(
                    {'name': 'Field Service', 'allow_billable': False, 'billing_type': 'not_billable'})
            service_task_id = self.env['project.task'].create({
                'name': self.name,
                'project_id': service_project_id.id,
                'date_deadline': self.deadline,
                'company_id': self.company_id.id,
                'user_ids': self.user_id,
                'ticket_id': self.id
            })
            self.service_task_id = service_task_id.id

    @api.onchange('customer_id')
    def _onchange_customer_id(self):
        self.email = self.customer_id.email

    @api.model_create_multi
    def create(self, vals):
        """ Sequence for support service tickets """
        if vals[0].get('ticket', _('New')) == _('New'):
            vals[0]['ticket'] = self.env['ir.sequence'].next_by_code(
                'support.service.ticket') or 'New'
        if 'team_id' in vals[0] and not vals[0]['team_id'] or 'team_id' not in \
                vals[0]:
            no_team = self.env['support.service.team'].search(
                [('name', '=', 'Administrators'),
                 ('company_id', '=', self.env.company.id)])
            if not no_team:
                no_team = self.env['support.service.team'].create({
                    'name': 'Administrators',
                    'manager_id': self.env['res.users'].search(
                        [('groups_id', '=', self.env.ref(
                            'cyllo_support_service.group_cyllo_support_service_team_manager').id)],
                        limit=1).id,
                    'company_id': self.env.company.id
                })
            vals[0]['team_id'] = no_team.id
        res = super(SupportServiceTicket, self).create(vals)
        res.message_subscribe(partner_ids=res.customer_id.ids)
        return res

    def action_assign_ticket(self):
        """ Function to assign ticket to a person and changing stage to
        'in progress' and also sending mail to customer to inform the ticket is
        'in progress' """
        if self.customer_id == False:
            partner = self.env['res.partner'].search(
                [('email', '=', self.email)])
            if partner:
                self.customer_id = partner.id
                return
            else:
                email_string = self.email_from
                start_index = email_string.index('"')
                end_index = email_string.rindex('"')
                return {
                    'type': 'ir.actions.act_window',
                    'res_model': 'res.partner',
                    'views': [[False, 'form']],
                    'view_mode': 'form',
                    'target': 'new',
                    'context': {
                        'default_email': self.email,
                        'default_name': email_string[start_index + 1: end_index]
                    },

                }
        if self.sale_order_item_id:
            self.sale_order_item_id.ticket_reference = self.id
        if self.user_id and self.deadline:
            user_employee = self.env['hr.employee'].search(
                [('user_id', '=', self.env.user.id)])
            assignee_employee = self.env['hr.employee'].search(
                [('user_id', '=', self.user_id.id)])
            if bool(user_employee):
                if bool(assignee_employee):
                    self.stage_id = self.env.ref(
                        'cyllo_support_service.support_service_stage_in_progress').id
                    mail_template_exec = self.env.ref(
                        'cyllo_support_service.mail_template_support_service')
                    mail_template_exec['email_from'] = self.env.user.work_email
                    mail_template_exec['email_to'] = self.customer_id.email
                    mail_template_exec['email_cc'] = self.user_id.work_email
                    mail_template_exec.sudo().send_mail(self._origin.id,
                                                        force_send=True)
                    # Adding a message in the chatter to inform that the mail
                    # sent or not
                    body = f"""Email sent to {self.customer_id.name} and {self.user_id.name}"""
                    self.message_post(body=body, subject="TICKET CREATED")
                else:
                    raise UserError(
                        'Cannot assign to the person who is not an employee')
            else:
                raise UserError('you have no permission to assign tickets')
        elif not self.user_id:
            raise UserError('Assignee field is empty')
        else:
            raise UserError('Add a deadline to the ticket')

    def action_pause_ticket(self, res_id):
        """ Function that change the ticket to 'hold' stage """
        support_service = self.env['support.service.ticket'].browse(res_id)
        self.write({'timer_toggle': False, })
        support_service.stage_id = self.env.ref(
            'cyllo_support_service.support_service_stage_on_hold').id

    def action_resume_ticket(self, res_id):
        """ Function to change the ticket stage to 'in progress' """
        support_service = self.env['support.service.ticket'].browse(res_id)
        self.write({'timer_toggle': False, })
        support_service.write({
            'stage_id': self.env.ref(
                'cyllo_support_service.support_service_stage_in_progress').id})

    def action_cancel_ticket(self):
        """ Function to change the ticket stage to 'cancel' """
        self.stage_id = self.env.ref(
            'cyllo_support_service.support_service_stage_canceled').id

    def action_close_ticket(self):
        """ Function to change the ticket stage to 'close' """
        self.stage_id = self.env.ref(
            'cyllo_support_service.support_service_stage_closed').id

    def action_stop_ticket(self):
        """ Function to change the ticket 'stop' """
        return {
            'name': _("Confirm Timesheet"),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'ticket.timesheet.confirm',
            'target': 'new',
            'context': {
                'default_ticket_id': self.id,
                'default_unit_amount': self.timesheet_time,
            },
        }

    def action_done_ticket(self):
        """ Function to change ticket stage to 'done' and sent mail to the
        customer to inform about work completion """
        if self.is_paid and self.ticket_order_id:
            self.ticket_invoice_ids = self.env['account.move'].search(
                [('invoice_origin', '=', self.ticket_order_id.name),
                 ('move_type', '!=', 'out_refund')])
            for rec in self.env['account.move'].search(
                    [('invoice_origin', '=', self.ticket_order_id.name),
                     ('state', '=', 'draft')]):
                rec.state = 'posted'
        self.stage_id = self.env.ref(
            'cyllo_support_service.support_service_stage_solved').id
        mail_template_exec = self.env.ref(
            'cyllo_support_service.mail_template_support_services')
        mail_template_exec['email_from'] = self.user_id.work_email
        mail_template_exec['email_to'] = self.customer_id.email
        mail_template_exec.sudo().send_mail(self._origin.id, force_send=True)
        # Adding a message in the chatter to inform that the mail sent or not
        body = f"""Work done mail sent to {self.customer_id.name}"""
        self.message_post(body=body, subject="ISSUE SOLVED")

    def action_create_invoice(self):
        """ Function to create invoice """
        self.ticket_order_id = ''
        if self.timesheet_ids:
            # Changing stage to 'to invoice' stage
            self.stage_id = self.env.ref(
                'cyllo_support_service.support_service_stage_to_invoice').id
            order_line_values = []
            product = self.env['product.product'].search(
                [('name', '=', self.team_id.name)], limit=1)
            if not product:
                product = self.env['product.product'].create(
                    {'name': self.team_id.name,
                     'detailed_type': 'service'})
            if self.sale_order_item_id:
                self.is_sale_order = True
                sale_order = self.sale_order_item_id
                for line in self.timesheet_ids:
                    order_line_values.append({
                        'order_id': sale_order.id,
                        'product_id': product.id,
                        'product_uom_qty': line.unit_amount,
                        'price_unit': line.employee_id.hourly_cost,
                    })
                self.env['sale.order.line'].create(order_line_values)
                self.ticket_sale_order = sale_order.id
                self.ticket_order_id = sale_order
                # Returning the sale order
                return {
                    'name': "Sale Order",
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'sale.order',
                    'res_id': sale_order.id,
                    'view_id': self.env.ref('sale.view_order_form').id,
                    'target': 'current',
                    'context': "{'create': False}"
                }
            else:
                # Creating invoice
                self.is_invoice_status = True
                invoice = self.env['account.move'].create({
                    'partner_id': self.customer_id.id,
                    'move_type': 'out_invoice',
                    'ticket_id': self.id,
                    'line_ids': [Command.create(
                        {'name': timesheet.name, 'product_id': product.id,
                         'quantity': timesheet.unit_amount,
                         'price_unit': timesheet.employee_id.hourly_cost, }) for
                        timesheet in self.timesheet_ids]
                })
                self.ticket_invoice_ids = invoice
                return {
                    'name': "Invoice",
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'account.move',
                    'res_id': invoice.id,
                    'view_id': self.env.ref('account.view_move_form').id,
                    'target': 'current',
                    'context': "{'create': False}"
                }
        else:
            raise UserError('Nothing to invoice')

    def action_sale_order(self):
        """ Function to show the sale order when clicking the smart button """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Sale Order',
            'view_mode': 'tree,form',
            'res_model': 'sale.order',
            'domain': [('id', '=', self.ticket_sale_order)],
            'context': "{'create': False}"
        }

    def action_get_invoice(self):
        """ Function to show the invoice when clicking the smart button """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Invoice',
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'domain': [('id', '=', self.ticket_invoice_ids.id)],
            'context': "{'create': False}"
        }

    def action_get_repair(self):
        """ Function to show the repair when clicking the smart button """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Repair',
            'view_mode': 'tree,form',
            'res_model': 'repair.order',
            'domain': [('ticket_id', '=', self.id)],
            'context': "{'create': False}"
        }

    def action_get_task(self):
        """ Function to show the tasks when clicking the smart button """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Tasks',
            'view_mode': 'tree,form',
            'res_model': 'project.task',
            'domain': [('id', '=', self.service_task_id.id)],
            'context': "{'create': False}"
        }

    def action_create_repair_order(self):
        """
       Create a repair order based on the current support service ticket.

       This method creates a new repair order with information derived from the current support service ticket.
       It sets the partner, internal notes, ticket reference, and picking type for the repair order.

       :return: The created repair order.
       :rtype: odoo.models.Recordset
       """
        return {
            'name': _("Repair"),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'repair.order.wizard',
            'target': 'new',
            'context': {
                'default_partner_id': self.customer_id.id,
                'default_internal_notes': self.description,
                'default_ticket_id': self.id,
            },
        }

    def action_create_refund(self):
        """
        Open a new window to create a refund using the 'account.move.reversal' model.

        If 'sale_order_item_id' is present, the method returns an action to open a new window
        for creating a refund. It pre-fills the default values for 'sale_order_id',
        'move_ids' based on related invoices, and 'ticket_id'.

        :return: Dictionary representing an action to open a new window for creating a refund.
        :raise MissingError: If 'sale_order_item_id' is not found.
        """
        return {
            'name': _("Refund"),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.move.reversal',
            'target': 'new',
            'context': {
                'default_ticket_id': self.id,
                'default_reason': f"Service Ticket #{self.id} - {self.name}",
            },
        }

    def _create_field_service_task(self):
        service_project_id = self.env['project.project'].sudo().search(
            [('name', '=', 'Field Service')])
        if not service_project_id:
            service_project_id = self.env['project.project'].create(
                {'name': 'Field Service'})
        service_task_id = self.env['project.task'].create({
            'name': self.name,
            'project_id': service_project_id.id,
            'ticket_id': self.id
        })
        self.service_task_id = service_task_id.id

    @api.model
    def message_new(self, msg_dict, custom_values=None):
        """Fetch the mail details such as email address , author from ,
        receiver name,Message and subject ,etc..
        for creating a ticket."""
        self = self.with_context(default_user_id=False)
        email_from = msg_dict.get('from')
        start_index = msg_dict.get('from').find('<')
        end_index = msg_dict.get('from').find('>')
        email_address = email_from[
            start_index + 1:end_index].strip() if start_index != -1 and end_index != -1 else email_from
        email_name = email_from[:start_index].strip() if start_index != -1 else email_address
        email_name = email_name.strip('\"')
        author_id = msg_dict.get('author_id', False)
        # If no author_id, create a new partner (res.partner)
        if not author_id and email_address:
            partner = self.env['res.partner'].sudo().create({
                'name': email_name or email_address,
                'email': email_address,
            })
            author_id = partner.id
        if custom_values is None:
            custom_values = {}
        # Build ticket default values
        defaults = {
            'name': msg_dict.get('subject') or _("No Subject"),
            'email': email_address,
            'customer_id': author_id,
            'description': msg_dict.get('body'),
        }

        defaults.update(custom_values)
        return super(SupportServiceTicket, self).message_new(msg_dict,
                                                             custom_values=defaults)

    # providing name for report in the portal
    def _get_report_base_filename(self):
        self.ensure_one()
        return 'Support Service Ticket- %s' % self.name

    def _expand_states(self, states, domain, order):
        """Function used to expand support service stage"""
        return self.env['support.service.stage'].search([])

    @api.model
    def get_overview(self):
        """ Function to calculate all values for the overview"""
        # Declaring a dictionary that contain all the values
        result = {
            'all_tickets': 0,
            'high_priority': 0,
            'urgent': 0,
            'failed_ticket_count': 0,
            'failed_high_priority_ticket_count': 0,
            'failed_urgent_ticket_count': 0,
            'my_today_closed_ticket_count': 0,
            'my_today_success_rate': 0,
            'my_last_seven_days_closed_ticket_count': 0,
            'my_last_seven_days_success_rate': 0,
        }
        # Taking the count of open tickets of current user in priority base
        all_tickets = self.search_count([('user_id', '=', self.env.user.id),
                                         ('stage_id.is_closed', '=', False),
                                         ('stage_id.is_canceled', '=', False)])
        high_priority = self.search_count(
            [('user_id', '=', self.env.user.id), ('priority', '=', '2'),
             ('stage_id.is_closed', '=', False), ('stage_id.is_canceled', '=', False)])
        urgent = self.search_count(
            [('user_id', '=', self.env.user.id), ('priority', '=', '3'),
             ('stage_id.is_closed', '=', False), ('stage_id.is_canceled', '=', False)])
        # Calculating the number of failed tickets of the current user
        failed_ticket_count = self.search_count(
            [('user_id', '=', self.env.user.id),
             ('deadline', '<', fields.Datetime.today()),
             ('stage_id.is_closed', '=', False),
             ('stage_id.is_canceled', '=', False)])
        # Calculating the number of failed high priority tickets of the
        # current user
        failed_high_priority_ticket_count = self.search_count(
            [('user_id', '=', self.env.user.id),
             ('deadline', '<', fields.Datetime.today()),
             ('stage_id.is_canceled', '=', False),
             ('stage_id.is_closed', '=', False), ('priority', '=', '2')])
        # Calculating the number of failed urgent tickets of the current user
        failed_urgent_ticket_count = self.search_count(
            [('user_id', '=', self.env.user.id),
             ('deadline', '<', fields.Datetime.today()),
             ('stage_id.is_canceled', '=', False),
             ('stage_id.is_closed', '=', False), ('priority', '=', '3')])
        # Calculating count of tickets closed today of current user
        today = fields.date.today()
        my_today_closed_ticket_count = self.search_count(
            [('user_id', '=', self.env.user.id), (
                'closed_date', '>=',
                datetime.combine(today, datetime.min.time())),
             (
                 'closed_date', '<=',
                 datetime.combine(today, datetime.max.time())),
             ('stage_id.is_closed', '=', True)])
        # Calculating success rate of current user
        closed_ticket_count = self.search_count([('closed_date', '>=',
                                                  datetime.combine(today,
                                                                   datetime.min.time())),
                                                 ('closed_date', '<=',
                                                  datetime.combine(today,
                                                                   datetime.max.time())),
                                                 ('user_id', '=',
                                                  self.env.user.id)])
        passed_ticket_count = self.search_count([('closed_date', '>=',
                                                  datetime.combine(today,
                                                                   datetime.min.time())),
                                                 ('closed_date', '<=',
                                                  datetime.combine(today,
                                                                   datetime.max.time())),
                                                 ('user_id', '=',
                                                  self.env.user.id),
                                                 ('is_failed', '=', False)])
        if passed_ticket_count:
            my_today_success_rate = round(
                ((passed_ticket_count / closed_ticket_count) * 100), 2)
        else:
            my_today_success_rate = 0
        # Calculating count of closed tickets in last seven days of current user
        one_week_back_date = datetime.now() - timedelta(days=6)
        my_last_seven_days_closed_ticket_count = self.search_count(
            [('user_id', '=', self.env.user.id),
             ('stage_id.is_closed', '=', True),
             ('closed_date', '>=', one_week_back_date)])
        # Calculating success rate in last seven days of current user
        closed_ticket_count = self.search_count(
            [('closed_date', '>=', one_week_back_date),
             ('user_id', '=', self.env.user.id)])
        passed_ticket_count = self.search_count(
            [('closed_date', '>=', one_week_back_date),
             ('user_id', '=', self.env.user.id), ('is_failed', '=', False)])
        if passed_ticket_count:
            my_last_seven_days_success_rate = round(
                ((passed_ticket_count / closed_ticket_count) * 100), 2)
        else:
            my_last_seven_days_success_rate = 0
        # Assigning all the values to the dictionary
        result.update({
            "all_tickets": all_tickets,
            "high_priority": high_priority,
            "urgent": urgent,
            "failed_ticket_count": failed_ticket_count,
            "failed_high_priority_ticket_count": failed_high_priority_ticket_count,
            "failed_urgent_ticket_count": failed_urgent_ticket_count,
            "my_today_closed_ticket_count": my_today_closed_ticket_count,
            "my_today_success_rate": my_today_success_rate,
            "my_last_seven_days_closed_ticket_count": my_last_seven_days_closed_ticket_count,
            "my_last_seven_days_success_rate": my_last_seven_days_success_rate,
        })
        return result

    def check_support_service_inactivity(self):
        """
       Check and update the stage of inactive support service tickets.
       This method iterates through support service tickets, checks for inactivity based on team settings,
       and updates the stage if the specified inactivity threshold is exceeded.
       """
        today = fields.datetime.today()
        all_stage_ids = []
        for ticket in self.env['support.service.ticket'].search([]):
            team = ticket.team_id
            all_stage_ids.extend(
                record.stage_id for record in team.inactivity_ids)
            if team.closing_inactive_tickets and ticket.stage_id in all_stage_ids:
                difference = (
                        today.date() - ticket.stage_change_date.date()).days
                inactive_id = team.inactivity_ids.search(
                    [('stage_id', '=', ticket.stage_id.id)])
                if difference > inactive_id.no_of_inactive_days:
                    ticket.write({'stage_id': inactive_id.state_id.id})
