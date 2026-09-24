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
from ast import literal_eval
from datetime import datetime, timedelta
from itertools import groupby
from odoo import api, fields, models


class SupportServiceTeam(models.Model):
    """ Class defines support service Team model """
    _name = "support.service.team"
    _inherit = ['mail.thread', 'mail.alias.mixin']
    _description = "Support Service Team"

    name = fields.Char(help="Team name", required=True)
    manager_id = fields.Many2one('res.users', string="Team Manager",
                                 required=True, domain=lambda self: [
            ('groups_id', '=', self.env.ref(
                'cyllo_support_service.group_cyllo_support_service_team_manager').id)], )
    description = fields.Html(help="Description about the team")
    is_timesheet = fields.Boolean(string="Timesheet",
                                  help="Can add timesheet for the ticket")
    ticket_id = fields.Many2one('support.service.ticket', string="All tickets")
    state_id = fields.Many2one(related='ticket_id.stage_id', string="Stage")
    priority = fields.Selection(related='ticket_id.priority')
    inactivity_ids = fields.One2many('support.service.inactivity', 'team_id')
    closing_inactive_tickets = fields.Boolean(
        string="Ticket Closing Due to inactivity")
    open_count = fields.Integer(string="Open Ticket Count",
                                compute="_compute_open_count")
    unassigned_count = fields.Integer(string="Unassigned Ticket Count",
                                      compute="_compute_unassigned_count",
                                      help="Count of tickets in the team that are not assigned to a person")
    urgent_count = fields.Integer(string="Urgent Ticket Count",
                                  compute="_compute_urgent_count",
                                  help="Count of urgent priority tickets in the team")
    failed_ticket_count = fields.Integer(compute="_compute_failed_ticket_count",
                                         help="Count of failed tickets in the team")
    color = fields.Integer()
    success_rate = fields.Float(compute="_compute_success_rate",
                                help="Team wise success rate")
    working_hour_id = fields.Many2one('resource.calendar',
                                      string="Working Hours",
                                      help="Working time of the team")
    closed_ticket_count = fields.Integer(compute="_compute_closed_ticket_count",
                                         help="Count of closed tickets in the team")
    company_id = fields.Many2one('res.company', required=True,
                                 default=lambda self: self.env.company,
                                 help="Support service team company")
    is_paid = fields.Boolean(
        help="Check if the team is working for paid tickets")
    project_id = fields.Many2one("project.project",
                                 compute="_compute_project_id",
                                 store=True)

    def _compute_open_count(self):
        """ Function to calculate the count of open tickets """
        tickets = self.env['support.service.ticket'].read_group(
            [('stage_id.is_closed', '=', False),('stage_id.is_canceled','=',False),
            ('team_id', 'in', self.ids)],
            ['team_id'], ['team_id'])
        ticket_dict = dict(
            (data['team_id'][0], data['team_id_count']) for data in tickets)
        for team in self:
            team.open_count = ticket_dict.get(team.id)

    def _compute_unassigned_count(self):
        """ Function to calculate the count of unassigned tickets """
        tickets = self.env['support.service.ticket'].read_group(
            [('user_id', '=', False), ('team_id', 'in', self.ids)],
            ['team_id'], ['team_id'])
        ticket_dict = dict(
            (data['team_id'][0], data['team_id_count']) for data in tickets)
        for team in self:
            team.unassigned_count = ticket_dict.get(team.id)

    def _compute_urgent_count(self):
        """ Function to calculate the count of urgent priority tickets """
        tickets = self.env['support.service.ticket'].read_group(
            [('priority', '=', '3'), ('team_id', 'in', self.ids)],
            ['team_id'], ['team_id'])
        ticket_dict = dict(
            (data['team_id'][0], data['team_id_count']) for data in tickets)
        for team in self:
            team.urgent_count = ticket_dict.get(team.id)

    def _compute_failed_ticket_count(self):
        """ Function to calculate the count of failed tickets """
        now = fields.datetime.now()
        tickets = self.env['support.service.ticket'].read_group(
            [('deadline', '<', now), ('stage_id.is_closed', '=', False),
             ('stage_id.is_canceled', '=', False),
             ('team_id', 'in', self.ids)], ['team_id'],
            ['team_id'])
        ticket_dict = dict(
            (data['team_id'][0], data['team_id_count']) for data in tickets)
        for team in self:
            team.failed_ticket_count = ticket_dict.get(team.id)

    def _compute_success_rate(self):
        """ Function to calculate the success rate of the team"""
        one_week_back_date = datetime.now() - timedelta(days=6)
        tickets = self.env['support.service.ticket'].search_read(
            [('closed_date', '>=', one_week_back_date)],
            ['team_id', 'closed_date', 'is_failed'])
        grouped_tickets = {}
        closed_ticket_count_dict = {}
        passed_ticket_count_dict = {}
        for team_id, group in groupby(tickets, key=lambda x: x['team_id']):
            if team_id:
                grouped_tickets[team_id] = list(group)
                ticket_count = len(grouped_tickets[team_id])
                closed_ticket_count_dict.update({team_id[0]: ticket_count})
        for team_id, tickets in grouped_tickets.items():
            passed_tickets = [ticket for ticket in tickets if
                              not ticket['is_failed']]
            passed_ticket_count_dict[team_id[0]] = len(passed_tickets)
        for team in self:
            if team.id in closed_ticket_count_dict.keys():
                team.success_rate = (passed_ticket_count_dict[team.id] /
                                     closed_ticket_count_dict[team.id]) * 100
            else:
                team.success_rate = 0

    def _compute_closed_ticket_count(self):
        """ Function to compute the count of closed tickets in the team """
        one_week_back_date = datetime.now() - timedelta(days=6)
        for team in self:
            team.closed_ticket_count = self.env[
                'support.service.ticket'].search_count(
                [('stage_id.is_closed', '=', 'True'),
                 ('closed_date', '>=', one_week_back_date),
                 ('team_id', '=', team.id)])

    @api.depends('is_timesheet')
    def _compute_project_id(self):
        """
        Compute and set the project for the task based on the 'is_timesheet' field.

        This method is triggered by changes in the 'is_timesheet' field. If 'is_timesheet'
        is True and 'project_id' is not set, it creates a new project using the task's name
        as the project name and sets the 'project_id' accordingly.

        :return: None
        """
        if self.is_timesheet and not self.project_id:
            self.project_id = self.env['project.project'].create(
                {'name': self.name, 'allow_billable': False, 'billing_type': 'not_billable'})

    @api.constrains('is_timesheet')
    def _check_is_timesheet(self):
        """ Function to set the timesheet boolean field to True if it is
        a paid ticket """
        if not self.is_timesheet and self.is_paid:
            self.is_timesheet = True

    def action_get_team_tickets(self):
        """ Function returns all the tickets in the team """
        action = self.env['ir.actions.actions']._for_xml_id(
            "cyllo_support_service.action_view_team_tickets")
        action['context'] = {'default_team_id': self.id,
                             'search_default_team': True, 'create': True}
        return action

    def get_team_open_tickets(self):
        """ Function to get all the open tickets """
        action = self.env['ir.actions.actions']._for_xml_id(
            "cyllo_support_service.action_view_open_team_ticket")
        return action

    def get_team_unassigned_tickets(self):
        """ Function that returns unassigned tickets in the team """
        action = self.env['ir.actions.actions']._for_xml_id(
            "cyllo_support_service.action_view_unassigned_team_tickets")
        return action

    def get_team_urgent_tickets(self):
        """ Function that returns urgent priority tickets in the team """
        action = self.env['ir.actions.actions']._for_xml_id(
            "cyllo_support_service.action_view_urgent_team_tickets")
        return action

    def get_team_failed_tickets(self):
        """ Function that returns failed tickets in the team """
        action = self.env['ir.actions.actions']._for_xml_id(
            "cyllo_support_service.action_view_team_urgent_failed_tickets")
        return action

    def get_team_closed_tickets(self):
        """ Function to show all closed tickets of the team """
        action = self.env['ir.actions.actions']._for_xml_id(
            "cyllo_support_service.action_view_closed_team_tickets")
        return action

    def get_team_solved_tickets(self):
        """ Function to show all solved tickets of the team """
        action = self.env['ir.actions.actions']._for_xml_id(
            "cyllo_support_service.action_view_successfully_solved_team_tickets")
        return action

    def _alias_get_creation_values(self):
        """ Returns the default values for the alias creation. """
        values = super(SupportServiceTeam, self)._alias_get_creation_values()
        values['alias_defaults'] = defaults = literal_eval(
            self.alias_defaults or "{}")
        defaults['ticket_type'] = 'enquiries'
        defaults['team_id'] = self.id
        defaults['ticket_source'] = 'email'
        values['alias_model_id'] = self.env['ir.model']._get(
            'support.service.ticket').id
        return values