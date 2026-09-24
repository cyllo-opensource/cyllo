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
from datetime import datetime
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class DailyTarget(models.Model):
    _name = "daily.target"
    _description = "Daily Target"
    _order = "date desc, user_id, id desc"

    name = fields.Char(compute="_compute_name")
    date = fields.Date(required=True, default=fields.Date.today)
    user_id = fields.Many2one(
        'res.users',
        string="User",
        required=True,
        default=lambda self: self.env.user,
    )
    team_id = fields.Many2one(
        'helpdesk.team',
        string="Helpdesk Team",
        default=lambda self: self._default_team_id(),
    )
    ticket_count = fields.Integer(string="Ticket Count", default=0)
    success_rate = fields.Float(string="Success Rate", default=0.0)
    average_rating = fields.Float(string="Average Rating", default=0.0)
    achieved_ticket_count = fields.Integer(
        string="Achieved Ticket Count",
        compute="_compute_achieved_metrics",
    )
    achieved_success_rate = fields.Float(
        string="Achieved Success Rate",
        compute="_compute_achieved_metrics",
    )
    achieved_average_rating = fields.Float(
        string="Achieved Average Rating",
        compute="_compute_achieved_metrics",
    )

    _sql_constraints = [
        (
            'daily_target_unique_per_day',
            'unique(date, user_id, team_id)',
            'Only one daily target is allowed per user, date, and team.',
        ),
    ]

    @api.model
    def _default_team_id(self):
        ticket = self.env['helpdesk.ticket'].search(
            [('user_id', '=', self.env.user.id), ('team_id', '!=', False)],
            order='date desc, id desc',
            limit=1,
        )
        team = ticket.team_id or self.env['helpdesk.team'].search([], limit=1)
        return team.id if team else False

    @api.depends('date', 'user_id', 'team_id')
    def _compute_name(self):
        for target in self:
            parts = [target.user_id.name or "User"]
            if target.team_id:
                parts.append(target.team_id.name)
            parts.append(str(target.date or fields.Date.today()))
            target.name = " - ".join(parts)

    @api.depends('date', 'user_id', 'team_id')
    def _compute_achieved_metrics(self):
        rating_model = self.env['rating.rating']
        for target in self:
            start_dt = datetime.combine(target.date, datetime.min.time())
            end_dt = datetime.combine(target.date, datetime.max.time())
            ticket_domain = [
                ('user_id', '=', target.user_id.id),
                ('closed_date', '>=', start_dt),
                ('closed_date', '<=', end_dt),
                ('stage_id.is_closed', '=', True),
            ]
            if target.team_id:
                ticket_domain.append(('team_id', '=', target.team_id.id))
            tickets = self.env['helpdesk.ticket'].search(ticket_domain)
            target.achieved_ticket_count = len(tickets)
            if tickets:
                passed_tickets = tickets.filtered(lambda ticket: not ticket.sla_failed)
                target.achieved_success_rate = round(
                    (len(passed_tickets) / len(tickets)) * 100, 2
                )
            else:
                target.achieved_success_rate = 0
            rating_domain = [
                ('res_model', '=', 'helpdesk.ticket'),
                ('consumed', '=', True),
                ('create_date', '>=', start_dt),
                ('create_date', '<=', end_dt),
                ('helpdesk_user_id', '=', target.user_id.id),
            ]
            if target.team_id:
                rating_domain.append(('helpdesk_team_id', '=', target.team_id.id))
            ratings = rating_model.search(rating_domain)
            if ratings:
                target.achieved_average_rating = round(
                    sum(ratings.mapped('rating')) / len(ratings), 2
                )
            else:
                target.achieved_average_rating = 0

    @api.constrains('ticket_count', 'success_rate', 'average_rating')
    def _check_target_values(self):
        for target in self:
            if target.ticket_count < 0:
                raise ValidationError("Ticket count cannot be negative.")
            if target.success_rate < 0 or target.success_rate > 100:
                raise ValidationError("Success rate must be between 0 and 100.")
            if target.average_rating < 0 or target.average_rating > 5:
                raise ValidationError("Average rating must be between 0 and 5.")
