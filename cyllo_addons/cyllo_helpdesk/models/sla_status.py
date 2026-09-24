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
from odoo import fields, models


class SLAStatus(models.Model):
    _name = "sla.status"
    _description = "Helpdesk SLA Status"

    ticket_id = fields.Many2one('helpdesk.ticket', string="Ticket", help="Helpdesk tickets", ondelete='cascade')
    sla_id = fields.Many2one('helpdesk.sla', string="SLA Policy", help="SLA policy", ondelete='cascade')
    deadline = fields.Datetime(string="Deadline", help="Calculated SLA deadline")
    reached_datetime = fields.Datetime(string="Reached Datetime", help="When the target stage was reached")
    state = fields.Selection([
        ('ongoing', 'Ongoing'),
        ('pass', 'Pass'),
        ('fail', 'Fail')], string="Status", default='ongoing')

    def status_update(self):
        """ Update SLA statuses for all active tickets """
        all_tickets = self.env['helpdesk.ticket'].search([('sla_ids', '!=', False)])
        now = datetime.now()
        for ticket in all_tickets:
            work_hours = ticket.team_id.working_hour_id or ticket.company_id.resource_calendar_id
            if not (work_hours and ticket.create_date):
                continue
            for sla in ticket.sla_ids:
                # 1. Find existing status or create one
                status = self.search([
                    ('ticket_id', '=', ticket.id),
                    ('sla_id', '=', sla.id)
                ], limit=1)
                if not status:
                    status = self.create({
                        'ticket_id': ticket.id,
                        'sla_id': sla.id,
                        'state': 'ongoing'
                    })
                # If already passed or failed, skip logic unless we want to allow re-evaluation
                if status.state != 'ongoing':
                    continue

                # 2. Update Deadline (accounts for excluded stages)
                # `within_hour` is a *working-hours* budget resolved through
                # the calendar, while the excluded/paused duration is real
                # wall-clock time; only the working-hours budget goes through
                # plan_hours(), the excluded time is added back afterwards so
                # units are never mixed.
                base_deadline = work_hours.plan_hours(
                    sla.within_hour,
                    ticket.create_date,
                    compute_leaves=True
                )
                excluded_hours = ticket._get_excluded_duration(sla)
                new_deadline = base_deadline + timedelta(hours=excluded_hours)
                if status.deadline != new_deadline:
                    status.deadline = new_deadline
                # 3. Check if reached
                if ticket.stage_id.sequence >= sla.target_stage.sequence:
                    # Find first reach date in history
                    reach_history = self.env['helpdesk.stage.history'].search([
                        ('ticket_id', '=', ticket.id),
                        ('stage_id.sequence', '>=', sla.target_stage.sequence)
                    ], order='start_date asc', limit=1)
                    status.reached_datetime = reach_history.start_date if reach_history else now
                    status.state = 'pass' if status.reached_datetime <= status.deadline else 'fail'
                    if status.state == 'fail':
                        ticket.sla_failed = True
                    continue

                # 4. Check if failed (not reached but deadline passed)
                if status.deadline and now > status.deadline:
                    status.state = 'fail'
                    ticket.sla_failed = True

