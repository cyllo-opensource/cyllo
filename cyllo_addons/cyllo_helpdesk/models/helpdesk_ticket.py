# -*- coding: utf-8 -*-
#############################################################################
#
#    Cyllo Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cyllo(<https://www.cyllo.com>)
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
import random
import re
from datetime import datetime, timedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.addons.web.controllers.utils import clean_action


class HelpDeskTicket(models.Model):
    _name = "helpdesk.ticket"
    _description = "HelpDesk Ticket"
    _inherit = ['mail.activity.mixin', 'rating.mixin']

    active = fields.Boolean(
        string='Active', default=True, tracking=True,
        help='Archive a ticket to hide it from the default ticket list.',
    )
    ticket = fields.Char(string='Ticket ID', readonly=True,
                         default=lambda self: _('New'),
                         help="Helpdesk ticket ID")
    name = fields.Char(string="Name", help="Small description about the issue",
                       required=True)
    team_id = fields.Many2one('helpdesk.team', string="Helpdesk Team",
                              help="Helpdesk Team", required=True)
    priority = fields.Selection([('0', 'Normal'), ('1', 'Low'), ('2', 'High'),
                                 ('3', 'Very High')], default='0',
                                string="Priority")
    customer_id = fields.Many2one('res.partner', string="Customer",
                                  help="Customer of the ticket", required=True)
    email = fields.Char(string="Email", help="Customer email id", tracking=True)
    email_cc_ids = fields.Many2many(
        'res.partner',
        'helpdesk_ticket_email_cc_rel',
        'ticket_id',
        'partner_id',
        string="Email CC",
        domain=[('email', '!=', False)],
        tracking=True,
        help="Additional recipients for ticket emails. Select an existing "
             "contact or enter an email address to create a recipient tag.",
    )
    phone = fields.Char(string="Phone", help="Customer phone number", tracking=True)
    category_id = fields.Many2one('helpdesk.category', string="Category",
                                  help="Ticket category")
    tag_id = fields.Many2one('helpdesk.tag', string="Tag",
                             help="Legacy single ticket tag")
    tag_ids = fields.Many2many('helpdesk.tag', string="Tags",
                               help="Ticket tags")
    user_id = fields.Many2one('res.users', string="Assigned to",
                              default=lambda self: self.env.user,
                              help="The person to whom the ticket assigned to")
    company_id = fields.Many2one('res.company', string="Company",
                                 required=True,
                                 default=lambda self: self.env.company,
                                 help="Company for the helpdesk ticket")
    description = fields.Html(string="Description",
                              help="Description about the issue or question")
    internal_notes = fields.Html(string="Internal Notes",
                                 help="Internal notes visible only to staff")
    use_field_service = fields.Boolean(related='team_id.use_field_service')
    sla_ids = fields.Many2many('helpdesk.sla', string="SLA policy",
                               help="SLA policy for this ticket")
    sla_flag = fields.Boolean(default=False,
                              help="To check SLA policy set or not")
    sla_failed = fields.Boolean(string="SLA failed ticket", default=False,
                                help="Ticket that failed SLA policy")
    sla_deadline = fields.Datetime(compute='_compute_sla_deadline',
                                   string="SLA Deadline", store=True)
    sla_reached_date = fields.Datetime(compute='_compute_sla_deadline',
                                       string="SLA Reached Date", store=True)
    stage_id = fields.Many2one('helpdesk.stage', string="Status",
                               default=lambda self: self.env.ref(
                                   'cyllo_helpdesk.new_ticket').id,
                               readonly=False, copy=False, tracking=True,
                               group_expand='_expand_states',
                               ondelete="restrict",
                               track_visibility='onchange',
                               help="Help desk stages")
    stage_name = fields.Char(related='stage_id.name')
    sequence = fields.Integer(related='stage_id.sequence', string="Sequence",
                              help="Stage sequence number")
    date = fields.Datetime(default=fields.Datetime.now)
    closed_date = fields.Datetime()
    sla_status_ids = fields.One2many('sla.status', 'ticket_id',
                                     string="SLA Status",
                                     help="Status of helpdesk ticket")
    last_seven_days = fields.Datetime(compute="_compute_last_seven_days")
    open_ticket_average_hours = fields.Float(string="Open Hours",
                                             compute="_compute_average_open_hours",
                                             store=True)
    high_priority_ticket_average_hours = fields.Float(
        string="High Priority Open Hours",
        compute="_compute_high_priority_average_open_hours", store=True)
    urgent_ticket_average_hours = fields.Float(
        string="Urgent Ticket Open Hours",
        compute="_compute_urgent_ticket_average_open_hours", store=True)
    is_closed_today = fields.Boolean(string='Closed Today',
                                     compute='_compute_is_closed_today')
    sla_status_label = fields.Char(compute='_compute_sla_status_label',
                                   string="SLA Status")

    def _compute_sla_status_label(self):
        for ticket in self:
            ticket.sla_status_label = _(
                "Failed") if ticket.sla_failed else False

    def _notify_get_reply_to(self, default=None):
        """Use the helpdesk team's inbound alias for ticket conversations.

        Delegating to the team is important: ``mail.alias.mixin`` returns the
        configured alias (or the company's catchall address) and formats it
        for a threaded reply.  Returning the company or assignee mailbox here
        bypasses the incoming-mail route, so replies to automatic emails never
        reach the ticket chatter.
        """
        team_reply_to = self.mapped('team_id').sudo()._notify_get_reply_to(
            default=default,
        )
        reply_to = {
            ticket.id: team_reply_to.get(ticket.team_id.id)
            for ticket in self
            if ticket.team_id
        }
        tickets_without_team = self.filtered(lambda ticket: not ticket.team_id)
        if tickets_without_team:
            reply_to.update(
                super(HelpDeskTicket, tickets_without_team)._notify_get_reply_to(
                    default=default,
                )
            )
        return reply_to

    def _send_ticket_email(self, template, force_send=True):
        """Post a ticket template and send it with a valid Reply-To header.

        Sending a template directly with ``mail.template.send_mail`` creates an
        outgoing mail, but does not use the ticket's chatter composition path.
        Consequently some mail clients' replies cannot be resolved back to the
        ticket.  The composer path creates the outgoing message on this thread,
        so its Message-ID is available to the incoming-mail router.
        """
        self.ensure_one()
        composer = self.env['mail.compose.message'].with_context(
            default_composition_mode='comment',
            default_model=self._name,
            default_res_ids=self.ids,
            default_template_id=template.id,
        ).create({
            'message_type': 'comment',
            'subtype_id': self.env.ref('mail.mt_comment').id,
        })
        composer.write({
            'force_send': force_send,
        })
        _mails, messages = composer._action_send_mail()
        return messages.mapped('mail_ids')[:1].id

    # Parent-Child Linking
    parent_id = fields.Many2one('helpdesk.ticket', string='Parent Ticket',
                                help='Reference to the main ticket')
    child_ids = fields.One2many('helpdesk.ticket', 'parent_id',
                                string='Sub-tickets')
    source = fields.Selection([
        ('manual', 'Manual'),
        ('website', 'Website'),
        ('livechat', 'Livechat'),
        ('email', 'Email'),
    ], string='Source', default='manual', help='The source from which the ticket was created.')

    @api.constrains('parent_id')
    def _check_parent_id_recursion(self):
        if not self._check_recursion():
            raise UserError(
                _('Error! You cannot create recursive ticket dependencies.'))

    # Dependencies
    dependency_ids = fields.Many2many('helpdesk.ticket',
                                      'helpdesk_ticket_dependency_rel',
                                      'ticket_id', 'dependency_id',
                                      string='Dependencies')
    # Assignment
    team_member_ids = fields.Many2many('res.users',
                                       related='team_id.member_ids')
    # SLA Pause
    sla_paused = fields.Boolean(string='SLA Paused', default=False)
    sla_pause_date = fields.Datetime()
    total_paused_duration = fields.Float(string='Total Paused Duration (Hours)', default=0.0,
                                         help='Total duration spent in manual pause')
    use_sla = fields.Boolean(related='team_id.use_sla', string="Use SLA")
    use_credit_notes = fields.Boolean(related='team_id.use_credit_notes', string="Use Credit Notes")
    use_coupons = fields.Boolean(related='team_id.use_coupons', string="Use Coupons")
    use_gift_cards = fields.Boolean(related='team_id.use_gift_cards', string="Use Gift Cards")
    use_returns = fields.Boolean(related='team_id.use_returns', string="Use Returns")
    # use_replacements = fields.Boolean(related='team_id.use_replacements', string="Use Replacements")
    use_repairs = fields.Boolean(related='team_id.use_repairs', string="Use Repairs")
    use_timesheet = fields.Boolean(related='team_id.use_timesheet', string="Use Timesheets")
    use_sale_order = fields.Boolean(related='team_id.use_sale_order',
                                    string="Use Sale Order")
    use_field_service = fields.Boolean(related='team_id.use_field_service',
                                       string="Use Field Service")
    use_crm = fields.Boolean(related='team_id.use_crm', string="Use CRM")
    # Integrations (core)
    # Portal
    website_published = fields.Boolean(string='Visible in Portal', default=True)
    # Duplicate Detection
    duplicate_ticket_ids = fields.Many2many('helpdesk.ticket',
                                            compute='_compute_duplicate_tickets',
                                            string='Duplicate Tickets')
    has_duplicates = fields.Boolean(compute='_compute_duplicate_tickets',
                                    string='Has Duplicates')
    # Canned Response
    canned_response_ids = fields.Many2many('mail.shortcode',
                                           string='Canned Response')
    attachment_ids = fields.Many2many('ir.attachment', string='Attachments',
                                      help='Attach files to this ticket')

    @api.onchange('stage_id')
    def onchange_stage_id(self):
        stage_one = self.env.ref('cyllo_helpdesk.new_ticket')
        if self._origin.stage_id and self._origin.stage_id != stage_one and self.stage_id == stage_one:
            raise UserError('Cannot go back')

        # Dependency Check
        if self.stage_id.is_closed:
            unresolved_deps = self.dependency_ids.filtered(
                lambda t: not t.stage_id.is_closed)
            if unresolved_deps:
                raise UserError(
                    _("Cannot close ticket until dependencies are resolved: %s") % (
                        ", ".join(unresolved_deps.mapped('ticket'))))

    @api.onchange('team_id')
    def _onchange_team_id_assignment(self):
        """Handle automated assignment when the team or skills are changed."""
        if not self.team_id:
            return

        manager_partner = self.team_id.manager_id.partner_id
        if not self.email_cc_ids and manager_partner.email:
            self.email_cc_ids = manager_partner

        method = self.team_id.assignment_method
        members = self.team_id.member_ids

        if method == 'manual':
            self.user_id = False
        elif method == 'random' and members:
            self.user_id = random.choice(members.ids)
        elif method == 'round_robin' and members:
            # Load-balanced assignment: find member with least open tickets
            ticket_counts = {}
            for member in members:
                count = self.env['helpdesk.ticket'].search_count([
                    ('user_id', '=', member.id),
                    ('stage_id.is_closed', '=', False)
                ])
                ticket_counts[member] = count
            if ticket_counts:
                best_member = min(ticket_counts, key=ticket_counts.get)
                self.user_id = best_member.id

    @api.onchange('customer_id')
    def _onchange_customer_id(self):
        """Set customer email and phone if available."""
        if self.customer_id:
            if self.customer_id.email:
                self.email = self.customer_id.email
            else:
                self.email = None
            if self.customer_id.phone:
                self.phone = self.customer_id.phone
            else:
                self.phone = None
        else:
            self.email = None
            self.phone = None

    @api.depends('sla_status_ids.deadline', 'sla_status_ids.reached_datetime',
                 'sla_status_ids.state')
    def _compute_sla_deadline(self):
        for ticket in self:
            ongoing = ticket.sla_status_ids.filtered(
                lambda s: s.state == 'ongoing')
            ticket.sla_deadline = min(
                ongoing.mapped('deadline')) if ongoing else False
            reached = ticket.sla_status_ids.filtered(
                lambda s: s.state == 'pass' and s.reached_datetime)
            ticket.sla_reached_date = max(
                reached.mapped('reached_datetime')) if reached else False

    @api.depends('name', 'customer_id', 'description', 'create_date',
                 'category_id', 'canned_response_ids')
    def _compute_duplicate_tickets(self):
        for ticket in self:
            if not ticket.customer_id:
                ticket.duplicate_ticket_ids = [(5, 0, 0)]
                ticket.has_duplicates = False
                continue
            # Mandatory criteria: Same customer and Same day
            ticket_date = (ticket.create_date or fields.Datetime.now()).date()
            date_start = datetime.combine(ticket_date, datetime.min.time())
            date_end = datetime.combine(ticket_date, datetime.max.time())
            domain = [
                ('customer_id', '=', ticket.customer_id.id),
                ('create_date', '>=', date_start),
                ('create_date', '<=', date_end),
                ('stage_id.is_closed', '=', False),
            ]
            if ticket.id:
                domain.append(('id', '!=', ticket._origin.id))
            potential_matches = self.search(domain)
            duplicate_ids = []
            for match in potential_matches:
                score = 0
                if ticket.name and match.name == ticket.name:
                    score += 1
                if ticket.category_id and match.category_id == ticket.category_id:
                    score += 1
                if ticket.description and match.description == ticket.description:
                    score += 1
                # Comparing many2many field (only if not empty)
                if ticket.canned_response_ids and set(
                        match.canned_response_ids.ids) == set(
                    ticket.canned_response_ids.ids):
                    score += 1
                if score >= 2:
                    duplicate_ids.append(match.id)
            ticket.duplicate_ticket_ids = [(6, 0, duplicate_ids)]
            ticket.has_duplicates = bool(duplicate_ids)

    @api.depends('crm_lead_ids')
    def _compute_integration_counts(self):
        for ticket in self:
            ticket.crm_lead_count = len(ticket.crm_lead_ids)

    @api.model_create_multi
    def create(self, vals_list):
        """ Sequence for helpdesk tickets and stage history """
        for vals in vals_list:
            if not vals.get('email_cc_ids') and vals.get('team_id'):
                manager_partner = self.env['helpdesk.team'].browse(
                    vals['team_id']).manager_id.partner_id
                if manager_partner.email:
                    vals['email_cc_ids'] = [fields.Command.set(
                        manager_partner.ids)]
            ticket_number = self.env['ir.sequence'].next_by_code(
                'helpdesk.ticket')
            if not ticket_number:
                raise UserError(_('Unable to generate a helpdesk ticket number.'))
            vals['ticket'] = ticket_number
        res = super(HelpDeskTicket, self).create(vals_list)
        for ticket in res:
            ticket._assign_ticket()
            # Automatically apply SLA policies on creation if not manually specified
            if not ticket.sla_ids and ticket.team_id.use_sla:
                sla_policies = ticket._get_sla_policies()
                if sla_policies:
                    ticket.sla_ids = [(6, 0, sla_policies.ids)]
                    ticket.sla_flag = True
            # Trigger status sync and deadline calculation
            ticket._update_sla_statuses()
            if ticket.stage_id:
                self.env['helpdesk.stage.history'].create({
                    'ticket_id': ticket.id,
                    'stage_id': ticket.stage_id.id,
                    'start_date': fields.Datetime.now(),
                })

            # Automated confirmation email when a new ticket is created
            mail_template = self.env.ref('cyllo_helpdesk.help_desk_mail_template',
                                         raise_if_not_found=False)
            if mail_template:
                if not ticket.email and ticket.customer_id and ticket.customer_id.email:
                    ticket.email = ticket.customer_id.email
                if ticket.customer_id:
                    ticket.message_subscribe(partner_ids=ticket.customer_id.ids)
                # Use the mail-template send path rather than posting the
                # template as a chatter comment.  The latter turns template
                # recipients into notifications and does not retain the CC
                # header on the outgoing mail.
                ticket._send_ticket_email(mail_template)
        return res

    def _rating_get_partner(self):
        self.ensure_one()
        return self.customer_id or super()._rating_get_partner()

    def copy(self, default=None):
        default = dict(default or {})
        default['name'] = '%s (copy)' % self.name
        return super(HelpDeskTicket, self).copy(default)

    @api.model
    def message_new(self, msg_dict, custom_values=None):
        """Create a ticket for a new email, or attach a reply to its ticket.

        Cyllo normally identifies replies through the ``In-Reply-To`` and
        ``References`` headers.  Some mail clients and forwarding rules remove
        those headers, but the confirmation template always retains the ticket
        number in its subject.  Use that number as a safe fallback so that the
        reply is posted to the existing ticket chatter instead of opening a
        second ticket.
        """
        subject = msg_dict.get('subject') or ''
        ticket_match = re.search(r'\[\s*Ticket\s*#\s*([^\]]+?)\s*\]', subject,
                                 flags=re.IGNORECASE)
        if ticket_match:
            ticket = self.search([
                ('ticket', '=', ticket_match.group(1).strip()),
            ], limit=1)
            if ticket:
                return ticket

        if custom_values is None:
            custom_values = {}
        email_from = msg_dict.get('from')
        if email_from:
            custom_values['email'] = email_from
        # customer_id is required on the ticket, so find (or create) the
        # partner for the sender rather than leaving it empty for unknown
        # senders, which would make create() below fail and bounce the email.
        if not custom_values.get('customer_id') and email_from:
            partner = self.env['res.partner'].sudo().find_or_create(email_from)
            if partner:
                custom_values['customer_id'] = partner.id
        custom_values.update({
            'name': msg_dict.get('subject', _('No Subject')),
            'description': msg_dict.get('body', ''),
            'source': 'email',
        })
        return super().message_new(msg_dict, custom_values=custom_values)

    def message_update(self, msg_dict, update_vals=None):
        """Show an explicit chatter entry when an email reply reaches a ticket.

        ``mail.thread.message_update`` attaches the received email itself to
        this ticket.  The additional note makes that routing visible in the
        ticket chatter without changing the email body or affecting other
        mail-enabled models.
        """
        result = super().message_update(msg_dict, update_vals=update_vals)
        self.message_post(
            body=_("A reply has been received and linked to this record."),
        )
        return result

    def message_post(self, **kwargs):
        """ Link attachments from incoming messages to the ticket's attachment_ids field. """
        message = super(HelpDeskTicket, self).message_post(**kwargs)
        if message.attachment_ids:
            self.attachment_ids = [(4, att.id) for att in
                                   message.attachment_ids]
        return message

    def _assign_ticket(self):
        self.ensure_one()
        if self.user_id or not self.team_id or self.team_id.assignment_method == 'manual':
            return
        team = self.team_id
        if team.assignment_method == 'random':
            members = self.env['res.users'].search([('groups_id', 'in',
                                                     self.env.ref(
                                                         'cyllo_helpdesk.cyllo_helpdesk_user').id)])
            if members:
                import random
                self.user_id = random.choice(members.ids)
        elif team.assignment_method == 'round_robin':
            members = self.env['res.users'].search([
                ('groups_id', 'in',
                 self.env.ref('cyllo_helpdesk.cyllo_helpdesk_user').id)
            ], order='id')
            if members:
                last_user = team.last_assigned_user_id
                next_user = members[0]
                if last_user and last_user in members:
                    index = list(members).index(last_user)
                    if index < len(members) - 1:
                        next_user = members[index + 1]

                self.user_id = next_user.id
                team.sudo().last_assigned_user_id = next_user.id

    @api.onchange('customer_id', 'team_id', 'category_id', 'tag_ids')
    def _onchange_sla_policy_criteria(self):
        if self.team_id and self.team_id.use_sla:
            sla_policies = self._get_sla_policies()
            if sla_policies:
                self.sla_flag = True
                self.sla_ids = [(6, 0, sla_policies.ids)]
            else:
                self.sla_flag = False
                self.sla_ids = [(5,)]
        else:
            self.sla_flag = False
            self.sla_ids = [(5,)]

    def _get_sla_policies(self):
        """ Return SLA policies matching the current ticket criteria """
        self.ensure_one()
        if not self.team_id:
            return self.env['helpdesk.sla']

        domain = [('team_ids', 'in', [self.team_id.id])]
        if self.customer_id:
            domain += ['|', ('customer_ids', '=', False),
                       ('customer_ids', 'in', [self.customer_id.id])]
        else:
            domain += [('customer_ids', '=', False)]

        if self.category_id:
            domain += ['|', ('category_ids', '=', False),
                       ('category_ids', 'in', [self.category_id.id])]
        else:
            domain += [('category_ids', '=', False)]

        if self.tag_ids:
            domain += ['|', ('tag_ids', '=', False),
                       ('tag_ids', 'in', self.tag_ids.ids)]
        else:
            domain += [('tag_ids', '=', False)]

        return self.env['helpdesk.sla'].search(domain)

    @api.onchange('tag_id')
    def _onchange_tag_id(self):
        for ticket in self:
            if ticket.tag_id and ticket.tag_id not in ticket.tag_ids:
                ticket.tag_ids = [(4, ticket.tag_id.id)]

    def _expand_states(self, states, domain, order):
        return self.env['helpdesk.stage'].search([])

    def write(self, vals):
        if 'stage_id' in vals:
            new_stage_id = vals['stage_id']
            new_ticket_stage = self.env.ref(
                'cyllo_helpdesk.new_ticket', raise_if_not_found=False)
            # Enforce: ticket cannot be moved back to the New stage
            if new_ticket_stage and new_stage_id == new_ticket_stage.id:
                for ticket in self:
                    if ticket.stage_id and ticket.stage_id.id != new_ticket_stage.id:
                        raise UserError(
                            _("Cannot move ticket '%s' back to the New stage.") % ticket.name)
            # Enforce: ticket cannot be closed while it has unresolved dependencies
            closing_stage = self.env['helpdesk.stage'].browse(new_stage_id)
            if closing_stage.is_closed:
                for ticket in self:
                    unresolved_deps = ticket.dependency_ids.filtered(
                        lambda t: not t.stage_id.is_closed)
                    if unresolved_deps:
                        raise UserError(
                            _("Cannot close ticket '%s' until dependencies are resolved: %s") % (
                                ticket.name,
                                ", ".join(unresolved_deps.mapped('ticket'))))

        tickets_with_stage_change = self.env['helpdesk.ticket']
        if 'stage_id' in vals:
            tickets_with_stage_change = self.filtered(
                lambda t: t.stage_id.id != vals['stage_id'])
            for ticket in tickets_with_stage_change:
                # Close current history
                last_history = self.env['helpdesk.stage.history'].search([
                    ('ticket_id', '=', ticket.id),
                    ('end_date', '=', False)
                ], limit=1)
                if last_history:
                    last_history.end_date = fields.Datetime.now()
                # Create new history
                self.env['helpdesk.stage.history'].create({
                    'ticket_id': ticket.id,
                    'stage_id': vals['stage_id'],
                    'start_date': fields.Datetime.now()
                })
        result = super(HelpDeskTicket, self).write(vals)
        in_progress_stage = self.env.ref(
            'cyllo_helpdesk.in_progress_ticket').id
        solved_stage = self.env.ref('cyllo_helpdesk.solved_ticket').id
        in_progress_mail_template = self.env.ref(
            'cyllo_helpdesk.help_desk_in_progress_mail_template',
            raise_if_not_found=False,
        )
        solved_mail_template = self.env.ref(
            'cyllo_helpdesk.help_desk_rating_template',
            raise_if_not_found=False)
        if 'stage_id' in vals:
            for ticket in tickets_with_stage_change:
                # Filter children to only those that actually need a stage update
                # to prevent recursion and redundant writes.
                children_to_update = ticket.child_ids.filtered(
                    lambda t: t.stage_id.id != vals['stage_id'])
                if children_to_update:
                    children_to_update.write({'stage_id': vals['stage_id']})
                # Check stages for email notifications
                if ticket.stage_id.template_id:
                    ticket.with_context(mail_notify_force_send=True, force_send=True).message_post_with_source(
                        ticket.stage_id.template_id,
                        subtype_xmlid='mail.mt_comment',
                    )
                elif (ticket.stage_id.id == in_progress_stage
                      and in_progress_mail_template):
                    ticket.with_context(mail_notify_force_send=True, force_send=True).message_post_with_source(
                        in_progress_mail_template,
                        subtype_xmlid='mail.mt_comment',
                    )
                elif ticket.stage_id.id == solved_stage and solved_mail_template:
                    ticket.with_context(mail_notify_force_send=True, force_send=True).message_post_with_source(
                        solved_mail_template,
                        subtype_xmlid='mail.mt_comment',
                    )
        # SLA Status Sync and Reach Logic
        if 'sla_ids' in vals:
            self._update_sla_statuses()
        if 'stage_id' in vals:
            for ticket in self:
                for status in ticket.sla_status_ids.filtered(
                        lambda s: s.state == 'ongoing'):
                    if ticket.stage_id.sequence >= status.sla_id.target_stage.sequence:
                        status.reached_datetime = fields.Datetime.now()
                        status.state = 'pass' if status.reached_datetime <= status.deadline else 'fail'
                        if status.state == 'fail':
                            ticket.sla_failed = True
        return result

    def _update_sla_statuses(self):
        """ Ensure every SLA policy on the ticket has a status record """
        for ticket in self:
            if not ticket.create_date:
                continue
            for sla in ticket.sla_ids:
                existing = ticket.sla_status_ids.filtered(
                    lambda s: s.sla_id == sla)
                if not existing:
                    work_hours = ticket.team_id.working_hour_id or ticket.company_id.resource_calendar_id
                    status = self.env['sla.status'].create({
                        'ticket_id': ticket.id,
                        'sla_id': sla.id,
                        'state': 'ongoing',
                    })
                    # Calculate deadline immediately. `within_hour` is a
                    # working-hours budget resolved through the calendar;
                    # the excluded/paused duration is real wall-clock time,
                    # so it's added back after plan_hours() rather than
                    # folded into the working-hours argument.
                    if work_hours:
                        base_deadline = work_hours.plan_hours(
                            sla.within_hour,
                            ticket.create_date,
                            compute_leaves=True
                        )
                        excluded_hours = ticket._get_excluded_duration(sla)
                        status.deadline = base_deadline + timedelta(hours=excluded_hours)

    @api.model
    def get_overview(self):
        """ Function to calculate all values for the overview"""
        # Declaring a dictionary that contain all the values
        result = {
            'all_tickets': 0,
            'high_priority': 0,
            'urgent': 0,
            'average_open_hour': 0,
            'high_priority_average_open_hour': 0,
            'urgent_average_open_hour': 0,
            'failed_ticket_count': 0,
            'failed_high_priority_ticket_count': 0,
            'failed_urgent_ticket_count': 0,
            'my_today_closed_ticket_count': 0,
            'my_success_rate_ticket_count': 0,
            'my_average_rating': 0,
            'my_last_seven_days_closed_ticket_count': 0,
            'my_last_seven_days_success_rate': 0,
            'my_last_seven_days_average_rating': 0,
        }
        # Taking the count of tickets in priority base (filtered by my open tickets)
        my_open_tickets = self.search([
            ('user_id', '=', self.env.user.id),
            ('stage_id.is_closed', '=', False)
        ])
        all_tickets = len(my_open_tickets)
        high_priority = len(
            my_open_tickets.filtered(lambda t: t.priority == '2'))
        urgent = len(my_open_tickets.filtered(lambda t: t.priority == '3'))

        # Calculating the actual average open hours of the tickets (age)
        def compute_avg_age(tickets):
            if not tickets:
                return 0
            now = datetime.now()
            total_hours = sum(
                (now - t.create_date).total_seconds() / 3600.0 for t in tickets
                if t.create_date)
            return total_hours / len(tickets)

        average_open_hour = compute_avg_age(my_open_tickets)
        high_priority_average_open_hour = compute_avg_age(
            my_open_tickets.filtered(lambda t: t.priority == '2'))
        urgent_average_open_hour = compute_avg_age(
            my_open_tickets.filtered(lambda t: t.priority == '3'))
        # Calculating the number of failed tickets of the current user
        failed_ticket_count = self.search_count(
            [('user_id', '=', self.env.user.id), ('sla_flag', '=', True), (
                'stage_id.is_closed', '=', False), ('sla_failed', '=', True)])
        # Calculating the number of failed high priority tickets of the
        # current user
        failed_high_priority_ticket_count = self.search_count(
            [('user_id', '=', self.env.user.id),
             ('sla_flag', '=', True), ('stage_id.is_closed', '=', False),
             ('priority', '=', '2'), ('sla_failed', '=', True)])

        # Calculating the number of failed urgent tickets of the current user
        failed_urgent_ticket_count = self.search_count(
            [('user_id', '=', self.env.user.id),
             ('sla_flag', '=', True), ('stage_id.is_closed', '=', False),
             ('priority', '=', '3'), ('sla_failed', '=', True)])
        # Calculating count of tickets closed today of current user
        today = fields.date.today()
        my_today_closed_ticket_count = self.search_count(
            [('user_id', '=', self.env.user.id),
             ('closed_date', '>=',
              datetime.combine(today, datetime.min.time())),
             ('closed_date', '<=',
              datetime.combine(today, datetime.max.time())),
             ('stage_id.is_closed', '=', True)])
        # Calculating success rate of current user
        closed_ticket_count = self.search_count([
            ('closed_date', '>=', datetime.combine(today, datetime.min.time())),
            ('closed_date', '<=', datetime.combine(today, datetime.max.time())),
            ('user_id', '=', self.env.user.id)])
        passed_ticket_count = self.search_count([
            ('closed_date', '>=', datetime.combine(today, datetime.min.time())),
            ('closed_date', '<=', datetime.combine(today, datetime.max.time())),
            ('user_id', '=', self.env.user.id),
            ('sla_failed', '=', False)])
        if passed_ticket_count:
            my_success_rate_ticket_count = round(
                ((passed_ticket_count / closed_ticket_count) * 100), 2)
        else:
            my_success_rate_ticket_count = 0
        # Calculating average rating for current user
        my_average_rating = 0
        # Calculating count of closed tickets in last seven days of
        # current user
        one_week_back_date = datetime.now() - timedelta(days=6)
        my_last_seven_days_closed_ticket_count = self.search_count(
            [('user_id', '=', self.env.user.id),
             ('stage_id.is_closed', '=', True),
             ('closed_date', '>=', one_week_back_date),
             ])
        # Calculating success rate in last seven days of current user
        closed_ticket_count = self.search_count([
            ('closed_date', '>=', one_week_back_date),
            ('user_id', '=', self.env.user.id)])
        passed_ticket_count = self.search_count([
            ('closed_date', '>=', one_week_back_date),
            ('user_id', '=', self.env.user.id), ('sla_failed', '=', False)])
        if passed_ticket_count:
            my_last_seven_days_success_rate = round(
                ((passed_ticket_count / closed_ticket_count) * 100), 2)
        else:
            my_last_seven_days_success_rate = 0
        # Calculating last seven days average rating of current user
        my_last_seven_days_average_rating = 0
        # Assigning all the values to the dictionary
        result['all_tickets'] = all_tickets
        result['high_priority'] = high_priority
        result['urgent'] = urgent
        result['average_open_hour'] = round(average_open_hour, 2)
        result['high_priority_average_open_hour'] = round(
            high_priority_average_open_hour, 2)
        result['urgent_average_open_hour'] = round(urgent_average_open_hour, 2)
        result['failed_ticket_count'] = failed_ticket_count
        result[
            'failed_high_priority_ticket_count'] = failed_high_priority_ticket_count
        result['failed_urgent_ticket_count'] = failed_urgent_ticket_count
        result['my_today_closed_ticket_count'] = my_today_closed_ticket_count
        result['my_success_rate_ticket_count'] = my_success_rate_ticket_count
        result['my_average_rating'] = my_average_rating
        result[
            'my_last_seven_days_closed_ticket_count'] = my_last_seven_days_closed_ticket_count
        result[
            'my_last_seven_days_success_rate'] = my_last_seven_days_success_rate
        result[
            'my_last_seven_days_average_rating'] = my_last_seven_days_average_rating
        return result

    def get_acton(self, action_ref, title, search_view_ref):
        action = self.env['ir.actions.actions']._for_xml_id(action_ref)
        action = clean_action(action, self.env)
        if title:
            action['display_name'] = title
        if search_view_ref:
            action['search_view_id'] = self.env.ref(search_view_ref).read()[0]
        if 'views' not in action:
            action['views'] = [(False, view) for view in
                               action['view_mode'].split(",")]
        return action

    @api.onchange('stage_id')
    def _onchange_ticket_stage_id(self):
        if self.stage_id.is_closed:
            self.closed_date = fields.Datetime.now()
        else:
            self.closed_date = False

    def _compute_last_seven_days(self):
        self.last_seven_days = datetime.now() - timedelta(days=6)

    @api.depends("sla_ids")
    def _compute_average_open_hours(self):
        max_within_hour_values = []
        open_sla_tickets = self.search(
            [('user_id', '=', self.env.user.id), ('sla_flag', '=', True), (
                'stage_id.is_closed', '=', False)])
        within_hour_values = open_sla_tickets.mapped(
            lambda open_ticket: open_ticket.sla_ids.mapped('within_hour'))
        if within_hour_values:
            for hours in within_hour_values:
                if hours:
                    max_within_hour_values.append(max(hours))
        if len(max_within_hour_values):
            self.open_ticket_average_hours = sum(max_within_hour_values) / len(
                max_within_hour_values)
        else:
            self.open_ticket_average_hours = 0

    @api.depends('closed_date')
    def _compute_is_closed_today(self):
        today = fields.Date.today()
        for ticket in self:
            if ticket.closed_date and ticket.closed_date.date() == today:
                ticket.is_closed_today = True
            else:
                ticket.is_closed_today = False

    @api.depends("sla_ids")
    def _compute_high_priority_average_open_hours(self):
        max_high_priority_within_hour_values = []
        high_priority_open_sla_tickets = self.search(
            [('user_id', '=', self.env.user.id), ('sla_flag', '=', True), (
                'stage_id.is_closed', '=', False), ('priority', '=', '2')])
        high_priority_within_hour_values = high_priority_open_sla_tickets.mapped(
            lambda high_priority_ticket: high_priority_ticket.sla_ids.mapped(
                'within_hour'))
        if high_priority_within_hour_values:
            for hours in high_priority_within_hour_values:
                if hours:
                    max_high_priority_within_hour_values.append(max(hours))
        if len(max_high_priority_within_hour_values):
            high_priority_average_open_hour = sum(
                max_high_priority_within_hour_values) / len(
                max_high_priority_within_hour_values)
            self.high_priority_ticket_average_hours = high_priority_average_open_hour
        else:
            self.high_priority_ticket_average_hours = 0

    @api.depends("sla_ids")
    def _compute_urgent_ticket_average_open_hours(self):
        max_urgent_within_hour_values = []
        urgent_open_sla_tickets = self.search(
            [('user_id', '=', self.env.user.id), ('sla_flag', '=', True), (
                'stage_id.is_closed', '=', False),
             ('priority', '=', '3')])
        urgent_within_hour_values = urgent_open_sla_tickets.mapped(
            lambda urgent_ticket: urgent_ticket.sla_ids.mapped('within_hour'))
        if urgent_within_hour_values:
            for hours in urgent_within_hour_values:
                if hours:
                    max_urgent_within_hour_values.append(max(hours))
        if len(max_urgent_within_hour_values):
            self.urgent_ticket_average_hours = sum(
                max_urgent_within_hour_values) / len(
                max_urgent_within_hour_values)
        else:
            self.urgent_ticket_average_hours = 0

    @api.model
    def _cron_auto_close_tickets(self):
        teams = self.env['helpdesk.team'].search([('auto_close_days', '>', 0)])
        for team in teams:
            # Auto-close tickets
            close_date = datetime.now() - timedelta(days=team.auto_close_days)
            tickets_to_close = self.search([
                ('team_id', '=', team.id),
                ('stage_id.is_closed', '=', False),
                ('write_date', '<', close_date)
            ])
            if tickets_to_close:
                solved_stage = team.auto_close_stage_id or self.env.ref(
                    'cyllo_helpdesk.solved_ticket')
                tickets_to_close.write({'stage_id': solved_stage.id})
            # Send reminders
            if team.auto_close_reminder_days > 0:
                reminder_date = datetime.now() - timedelta(
                    days=team.auto_close_reminder_days)
                tickets_to_remind = self.search([
                    ('team_id', '=', team.id),
                    ('stage_id.is_closed', '=', False),
                    ('write_date', '<', reminder_date),
                    ('message_needaction', '=', False)
                    # Simple heuristic to avoid spamming
                ])
                for ticket in tickets_to_remind:
                    ticket._send_auto_close_reminder()

    def _send_auto_close_reminder(self):
        self.ensure_one()
        template = self.env.ref(
            'cyllo_helpdesk.help_desk_mail_template_auto_close_reminder',
            raise_if_not_found=False)
        if template:
            self._send_ticket_email(template)

    def action_toggle_sla_pause(self):
        for record in self:
            if record.sla_paused:
                # Add current pause duration to total
                if record.sla_pause_date:
                    duration = (fields.Datetime.now() - record.sla_pause_date).total_seconds() / 3600.0
                    record.total_paused_duration += duration
                record.sla_paused = False
                record.sla_pause_date = False
                record.message_post(body=_("SLA policy resumed."))
                # Re-calculate deadlines when resuming
                record._update_sla_statuses()
            else:
                record.sla_paused = True
                record.sla_pause_date = fields.Datetime.now()
                record.message_post(body=_("SLA policy paused."))

    def _escalate_ticket(self):
        """ Escalate ticket to manager if SLA fails """
        manager_group = self.env.ref('cyllo_helpdesk.cyllo_helpdesk_manager')
        managers = self.env['res.users'].search(
            [('groups_id', 'in', manager_group.id)])
        if managers:
            self.message_post(
                body=_(
                    "Ticket %s has failed SLA and is escalated to managers.") % self.ticket,
                partner_ids=managers.partner_id.ids,
                subtype_xmlid='mail.mt_comment'
            )

    def action_create_sale_order(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "sale.action_orders")
        action['res_model'] = 'sale.order'
        action['view_mode'] = 'form'
        action['views'] = [(self.env.ref('sale.view_order_form').id, 'form')]
        action['target'] = 'current'
        action['context'] = {
            'default_partner_id': self.customer_id.id,
            'default_helpdesk_ticket_id': self.id,
        }
        self.message_post(body=_("Sale Order creation initiated."))
        return action

    def _get_excluded_duration(self, sla_policy):
        """ Calculate total duration spent in excluded stages or manual pauses for a given SLA policy """
        self.ensure_one()
        total_duration = self.total_paused_duration

        # If currently paused, add duration since pause_date
        if self.sla_paused and self.sla_pause_date:
            total_duration += (fields.Datetime.now() - self.sla_pause_date).total_seconds() / 3600.0

        if not sla_policy.excluded_stage_ids:
            return total_duration

        history = self.env['helpdesk.stage.history'].search([
            ('ticket_id', '=', self.id),
            ('stage_id', 'in', sla_policy.excluded_stage_ids.ids)
        ])
        for record in history:
            if record.end_date:
                total_duration += record.duration
            else:
                # Still in an excluded stage, calculate duration up until now
                diff = fields.Datetime.now() - record.start_date
                total_duration += diff.total_seconds() / 3600.0
        return total_duration

    @api.onchange('canned_response_ids')
    def onchange_canned_response_ids(self):
        for ticket in self:
            if ticket.canned_response_ids:
                new_content = []
                for response in ticket.canned_response_ids:
                    if response.substitution:
                        new_content.append(response.substitution)
                if new_content:
                    combined_content = '<br/>'.join(new_content)
                    ticket.description = combined_content

    def action_view_duplicates(self):
        self.ensure_one()
        return {
            'name': _('Duplicate Tickets'),
            'type': 'ir.actions.act_window',
            'res_model': 'helpdesk.ticket',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.duplicate_ticket_ids.ids)],
            'target': 'current',
        }

    def action_view_refunds(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "account.action_move_out_refund_type")
        action['view_mode'] = 'list,form'
        action['domain'] = [('helpdesk_ticket_id', '=', self.id),
                            ('move_type', '=', 'out_refund')]
        return action

    def action_snooze(self):
        """Snooze next activity of current user by 7 days."""
        self.ensure_one()
        today = fields.Date.today()
        my_next_activity = self.activity_ids.filtered(lambda activity: activity.user_id == self.env.user)[:1]
        if my_next_activity:
            if my_next_activity.date_deadline < today:
                date_deadline = today + timedelta(days=7)
            else:
                date_deadline = my_next_activity.date_deadline + timedelta(days=7)
            my_next_activity.write({
                'date_deadline': date_deadline
            })
        return True
