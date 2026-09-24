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
from datetime import datetime, timedelta
from itertools import groupby
import ast
from odoo import fields, models, api, _


class HelpDeskTeam(models.Model):
    _name = "helpdesk.team"
    _description = "HelpDesk Team"
    _inherit = ['mail.alias.mixin']

    _sql_constraints = [
        ('name_unique', 'unique(name)', 'Helpdesk Team name must be unique!'),
    ]

    name = fields.Char(string="Name", help="Team name", required=1)
    description = fields.Html(string="Description", help="Description about the team")
    ticket_id = fields.Many2one('helpdesk.ticket', string="All tickets")
    user_id = fields.Many2one(related='ticket_id.user_id', string="Stage")
    state_id = fields.Many2one(related='ticket_id.stage_id', string="Stage")
    priority = fields.Selection(related='ticket_id.priority',
                                string="Priority")
    sla_flag = fields.Boolean(related='ticket_id.sla_flag', string="SLA Flag")
    sla_failed = fields.Boolean(compute="_compute_sla_failed_ticket",
                                string="SLA failed ticket",
                                help="Ticket that failed SLA policy")
    open_count = fields.Integer(string="Open Ticket Count",
                                compute="_compute_open_helpdesk_ticket_count")
    unassigned_count = fields.Integer(string="Unassigned Ticket Count",
                                      compute="_compute_unassigned_ticket_count",
                                      help="Count of tickets in the team that are not assigned to a person")
    urgent_count = fields.Integer(string="Urgent Ticket Count",
                                  compute="_compute_urgent_ticket_count",
                                  help="Count of urgent priority tickets in the team")
    failed_sla_count = fields.Integer(string="Failed Ticket Count",
                                      compute="_compute_failed_ticket_count",
                                      help="Count of failed tickets in the team")
    color = fields.Integer(string="Color")
    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.company,
        help="Company for this helpdesk team",
    )
    success_rate = fields.Float(compute="_compute_success_rate",
                                string="Success Rate",
                                help="Team wise success rate")
    working_hour_id = fields.Many2one('resource.calendar',
                                      string="Working Hours",
                                      help="Working time of the team")
    customer_rating = fields.Boolean(string="Customer Rating",
                                     help="Know the customer rating about the service")
    use_sla = fields.Boolean(string="Use SLA", default=True)
    use_timesheet = fields.Boolean(string="Use Timesheets", default=True)
    use_credit_notes = fields.Boolean(
        string="Use Credit Notes",
        help="Allow this team to create credit notes (refunds) directly from tickets.")
    use_coupons = fields.Boolean(
        string="Use Coupons",
        help="Allow this team to issue discount coupons directly from tickets.")
    use_field_service = fields.Boolean(
        string="Use Field Service",
        help="Allow this team to create and manage field service requests from tickets.")
    use_gift_cards = fields.Boolean(
        string="Use Gift Cards",
        help="Allow this team to issue gift cards directly from tickets.")
    use_crm = fields.Boolean(
        string="Use CRM",
        help="Allow this team to create CRM leads/opportunities from tickets.")
    use_returns = fields.Boolean(
        string="Use Returns",
        help="Allow this team to process product returns directly from tickets.")
    use_repairs = fields.Boolean(
        string="Use Repairs",
        help="Allow this team to create repair orders directly from tickets.")
    use_product_warranty = fields.Boolean(
        string="Use Product Warranty",
        help="Allow this team to manage product warranties directly from tickets.")
    use_website_ticket_creation = fields.Boolean(
        string="Website Ticket Creation",
        help="Allow this team to receive tickets created from the website form.",
    )
    use_livechat_ticket_creation = fields.Boolean(
        string="LiveChat Ticket Creation",
        help="Allow this team to receive tickets created from the livechat /ticket command.",
    )
    use_email_alias = fields.Boolean(
        string="Email Alias",
        help="Allow this team to receive tickets from an email alias.",
    )
    use_sale_order = fields.Boolean(
        string="Enable Sale Order Features",
        help="Allow this team to use Sale Order related features.",
    )
    use_confirmation_email = fields.Boolean(
        string="Confirmation Email",
        help="Send an automated confirmation email to the customer when a ticket is created via email.",
    )
    use_project = fields.Boolean(string="Use Project",
                                 help="Enable project task creation from tickets.")
    assignment_method = fields.Selection([
        ('manual', 'Manual'),
        ('random', 'Random'),
        ('round_robin', 'Round Robin'),
        ('skill', 'Skill-based')
    ], string='Assignment Method', default='manual',
        help="Method used to assign tickets to team members:\n"
             "- Manual: Tickets are not assigned automatically.\n"
             "- Random: Tickets are assigned to a random team member.\n"
             "- Round Robin: Tickets are assigned to team members in turn.\n"
             "- Skill-based: Tickets are assigned based on matching skills.")
    manager_id = fields.Many2one('res.users', string='Team Manager',
                                 help="Default recipient copied on ticket emails.")
    last_assigned_user_id = fields.Many2one('res.users', string='Last Assigned User', help="Used for Round Robin assignment")
    member_ids = fields.Many2many('res.users', string='Team Members', help="Users who can be assigned to tickets in this team")

    # Auto-close settings
    auto_close_days = fields.Integer(string='Auto-close after (days)', default=0, help="Tickets will be automatically closed after this many days of inactivity.")
    auto_close_reminder_days = fields.Integer(string='Auto-close reminder after (days)', default=0, help="A reminder will be sent this many days before the ticket is auto-closed.")
    auto_close_stage_id = fields.Many2one('helpdesk.stage', string='Auto-close Stage',
        default=lambda self: self.env.ref('cyllo_helpdesk.canceled_ticket', raise_if_not_found=False),
        help="Ticket will be moved to this stage once it is auto-closed.")
    closed_ticket_count = fields.Integer(
        compute="_compute_closed_ticket_count", string="Closed Ticket Count",
        help="Count of closed tickets in the team")
    rating_avg = fields.Float(compute="_compute_rating_avg",
                               string="Average Rating")
    rating_count = fields.Integer(compute="_compute_rating_avg",
                                   string="Rating Count")
    all_ticket_count = fields.Integer(compute="_compute_all_ticket_count", string="Total Tickets")
    sla_policy_count = fields.Integer(compute="_compute_sla_policy_count", string="SLA Policies")

    # Toggle-to-module mapping for auto-installation
    TOGGLE_MODULE_MAP = {
        'use_repairs': 'cyllo_helpdesk_repair',
        'use_timesheet': 'cyllo_helpdesk_timesheet',
        'use_returns': 'cyllo_helpdesk_stock',

        'use_coupons': 'cyllo_helpdesk_loyalty',
        'use_gift_cards': 'cyllo_helpdesk_loyalty',
        'use_crm': 'cyllo_helpdesk_crm',
        'use_field_service': 'cyllo_helpdesk_field_service',
        'use_product_warranty': 'cyllo_helpdesk_warranty',
        'use_website_ticket_creation': 'cyllo_helpdesk_website',
        'use_livechat_ticket_creation': 'cyllo_helpdesk_livechat',
        'use_sale_order': 'cyllo_helpdesk_sale',
        'use_credit_notes': 'cyllo_helpdesk_account',
        'use_project' : 'cyllo_helpdesk_project',
    }

    @api.model_create_multi
    def create(self, vals_list):
        teams = super(HelpDeskTeam, self).create(vals_list)
        all_modules = set()
        for vals in vals_list:
            for toggle, module_name in self.TOGGLE_MODULE_MAP.items():
                if vals.get(toggle):
                    all_modules.add(module_name)
        if all_modules and self.env.registry.ready and not self.env.registry._init:
            modules = self.env['ir.module.module'].sudo().search([
                ('name', 'in', list(all_modules)),
                ('state', '=', 'uninstalled'),
            ])
            if modules:
                modules.button_immediate_install()
        return teams

    def write(self, vals):
        res = super(HelpDeskTeam, self).write(vals)
        self._install_modules_from_toggles(vals)
        return res

    def _install_modules_from_toggles(self, vals):
        """Install modules based on enabled toggles in vals."""
        if not self.env.registry.ready or self.env.registry._init:
            return False
        modules_to_install = set()
        for toggle, module_name in self.TOGGLE_MODULE_MAP.items():
            if vals.get(toggle):
                modules_to_install.add(module_name)

        if modules_to_install:
            modules = self.env['ir.module.module'].sudo().search([
                ('name', 'in', list(modules_to_install)),
                ('state', '=', 'uninstalled'),
            ])
            if modules:
                return modules.button_immediate_install()
        return False

    def _alias_get_creation_values(self):
        values = super()._alias_get_creation_values()
        values['alias_model_id'] = self.env['ir.model']._get('helpdesk.ticket').id
        if self.id:
            values['alias_defaults'] = defaults = ast.literal_eval(self.alias_defaults or "{}")
            defaults['team_id'] = self.id
            values['alias_defaults'] = repr(defaults)
        return values

    def _compute_open_helpdesk_ticket_count(self):
        tickets = self.env['helpdesk.ticket'].read_group(
            [('stage_id.is_closed', '=', False), ('team_id', 'in', self.ids)],
            ['team_id'], ['team_id'])
        ticket_dict = dict(
            (data['team_id'][0], data['team_id_count']) for data in tickets)
        for team in self:
            team.open_count = ticket_dict.get(team.id)

    def _compute_unassigned_ticket_count(self):
        tickets = self.env['helpdesk.ticket'].read_group(
            [('user_id', '=', False), ('team_id', 'in', self.ids)],
            ['team_id'], ['team_id'])
        ticket_dict = dict(
            (data['team_id'][0], data['team_id_count']) for data in tickets)
        for team in self:
            team.unassigned_count = ticket_dict.get(team.id)

    def _compute_urgent_ticket_count(self):
        tickets = self.env['helpdesk.ticket'].read_group(
            [('priority', '=', '3'), ('team_id', 'in', self.ids)],
            ['team_id'], ['team_id'])
        ticket_dict = dict(
            (data['team_id'][0], data['team_id_count']) for data in tickets)
        for team in self:
            team.urgent_count = ticket_dict.get(team.id)

    def _compute_failed_ticket_count(self):
        tickets = self.env['helpdesk.ticket'].read_group(
            [('sla_flag', '=', True), ('sla_failed', '=', True),
             ('stage_id.is_closed', '=', False), ('team_id', 'in', self.ids)],
            ['team_id'], ['team_id'])
        ticket_dict = dict(
            (data['team_id'][0], data['team_id_count']) for data in tickets)
        for team in self:
            team.failed_sla_count = ticket_dict.get(team.id)

    def _compute_sla_failed_ticket(self):
        """Set team SLA flag when any ticket in the team has failed SLA."""
        failed_teams = self.env['helpdesk.ticket'].read_group(
            [('team_id', 'in', self.ids), ('sla_failed', '=', True)],
            ['team_id'],
            ['team_id'],
        )
        failed_team_ids = {
            data['team_id'][0] for data in failed_teams if data.get('team_id')
        }
        for team in self:
            team.sla_failed = team.id in failed_team_ids

    def action_team_settings(self):
        return {
            'name': 'Team Settings',
            'type': 'ir.actions.act_window',
            'res_model': 'helpdesk.team',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'current',
        }

    def action_get_team_tickets(self):
        action = self.env['ir.actions.actions']._for_xml_id(
            "cyllo_helpdesk.helpdesk_team_ticket_action")
        action['domain'] = [('team_id', '=', self.id)]
        action['context'] = {'default_team_id': self.id}
        return action

    def get_team_open_tickets(self):
        action = self.env['ir.actions.actions']._for_xml_id(
            "cyllo_helpdesk.helpdesk_team_open_ticket_action")
        action['domain'] = [('team_id', '=', self.id)]
        action['context'] = {
            'search_default_stage_id': True,
            'default_team_id': self.id,
        }
        return action

    def get_team_unassigned_tickets(self):
        action = self.env['ir.actions.actions']._for_xml_id(
            "cyllo_helpdesk.helpdesk_team_unassigned_ticket_action")
        action['domain'] = [('team_id', '=', self.id)]
        action['context'] = {
            'search_default_unassigned': True,
            'default_team_id': self.id,
        }
        return action

    def get_team_urgent_tickets(self):
        action = self.env['ir.actions.actions']._for_xml_id(
            "cyllo_helpdesk.helpdesk_team_urgent_ticket_action")
        action['domain'] = [('team_id', '=', self.id)]
        action['context'] = {
            'search_default_urgent': True,
            'default_team_id': self.id,
        }
        return action

    def get_team_failed_tickets(self):
        action = self.env['ir.actions.actions']._for_xml_id(
            "cyllo_helpdesk.helpdesk_team_failed_ticket_action")
        action['domain'] = [('team_id', '=', self.id)]
        action['context'] = {
            'search_default_failed': True,
            'default_team_id': self.id,
        }
        return action

    def _compute_success_rate(self):
        one_week_back_date = datetime.now() - timedelta(
            days=6)
        tickets = self.env['helpdesk.ticket'].search_read(
            [('closed_date', '>=', one_week_back_date), ('team_id', '!=', False)],
            ['sla_flag', 'team_id', 'closed_date', 'sla_failed'])
        sorted_tickets = sorted(tickets, key=lambda x: x['team_id'])
        grouped_tickets = {}
        closed_ticket_count_dict = {}
        passed_ticket_count_dict = {}
        for team_id, group in groupby(sorted_tickets,
                                      key=lambda x: x['team_id']):
            grouped_tickets[team_id] = list(group)
            ticket_count = len(grouped_tickets[team_id])
            closed_ticket_count_dict.update({team_id[0]: ticket_count})
        for team_id, tickets in grouped_tickets.items():
            passed_tickets = [ticket for ticket in tickets if
                              not ticket['sla_failed']]
            passed_ticket_count_dict[team_id[0]] = len(passed_tickets)
        for team in self:
            if team.id in closed_ticket_count_dict.keys():
                team.success_rate = (passed_ticket_count_dict[team.id] /
                                     closed_ticket_count_dict[team.id]) * 100
            else:
                team.success_rate = 0

    def _compute_closed_ticket_count(self):
        one_week_back_date = datetime.now() - timedelta(
            days=6)
        for team in self:
            team.closed_ticket_count = self.env[
                'helpdesk.ticket'].search_count(
                [('stage_id.is_closed', '=', True),
                 ('closed_date', '>=', one_week_back_date),
                 ('team_id', '=', team.id)])

    def get_team_closed_tickets(self):
        action = self.env['ir.actions.actions']._for_xml_id(
            "cyllo_helpdesk.helpdesk_team_closed_ticket_action")
        return action

    def get_team_solved_tickets(self):
        action = self.env['ir.actions.actions']._for_xml_id(
            "cyllo_helpdesk.helpdesk_team_successfully_solved_ticket_action")
        return action

    def _compute_rating_avg(self):
        for team in self:
            ratings = self.env['rating.rating'].search([
                ('helpdesk_team_id', '=', team.id),
                ('consumed', '=', True),
            ])
            if ratings:
                team.rating_avg = sum(ratings.mapped('rating')) / len(ratings)
                team.rating_count = len(ratings)
            else:
                team.rating_avg = 0
                team.rating_count = 0

    def _compute_all_ticket_count(self):
        for team in self:
            team.all_ticket_count = self.env['helpdesk.ticket'].search_count([('team_id', '=', team.id)])

    def _compute_sla_policy_count(self):
        for team in self:
            team.sla_policy_count = self.env['helpdesk.sla'].search_count([('team_ids', 'in', team.ids)])

    def action_view_team_sla_policies(self):
        self.ensure_one()
        return {
            'name': _('SLA Policies'),
            'type': 'ir.actions.act_window',
            'res_model': 'helpdesk.sla',
            'view_mode': 'tree,form',
            'domain': [('team_ids', 'in', self.id)],
            'target': 'current',
        }

    def action_view_team_rating(self):
        self.ensure_one()
        return {
            'name': _('Average Rating'),
            'type': 'ir.actions.act_window',
            'res_model': 'rating.rating',
            'view_mode': 'tree,form,pivot,graph',
            'domain': [('helpdesk_team_id', '=', self.id), ('consumed', '=', True)],
            'target': 'current',
        }

    @api.constrains('use_sla')
    def _check_use_sla(self):
        for team in self:
            if not team.use_sla:
                policies = self.env['helpdesk.sla'].search_count([('team_ids', 'in', team.ids)])
                if policies > 0:
                    raise models.ValidationError(_(
                        "You cannot disable SLA for team '%s' because it has active SLA policies. "
                        "Please remove or reassign the SLA policies first."
                    ) % team.name)
