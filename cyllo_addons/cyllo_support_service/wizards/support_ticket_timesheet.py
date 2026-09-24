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
from odoo import fields, models


class TicketTimesheetConfirm(models.TransientModel):
    """Wizard for logging time on support tickets and managing timers."""
    _name = 'ticket.timesheet.confirm'
    _description = 'Ticket Timesheet Confirm'

    unit_amount = fields.Float(string="Hours Spent")
    ticket_id = fields.Many2one('support.service.ticket', string="Ticket")
    note = fields.Char(string="Description")

    def ticket_log_time(self):
        """Log time on the related support ticket and stop the running timer.

        - Moves the ticket stage to 'In Progress'.
        - Sends a bus notification to stop the timer.
        - Creates a timesheet entry for the logged hours.
        """
        self.ticket_id.stage_id = self.env.ref(
            'cyllo_support_service.support_service_stage_in_progress').id
        channel = "TIMER-STOP"
        values = {
            "channel": channel,
            "timer_toggle": True,
        }
        self.env["bus.bus"]._sendone(channel, "stop_timer", values)
        self.env['account.analytic.line'].create({
            'ticket_id': self.ticket_id.id,
            'name': self.note,
            'project_id': self.ticket_id.team_id.project_id.id,
            'unit_amount': self.unit_amount,
        })

    def ticket_resume_timer(self):
        """Resume the timer for the related support ticket by sending a bus notification."""
        channel = "TIMER-STOP"
        values = {
            "channel": channel,
            "timer_toggle": True,
        }
        self.env["bus.bus"]._sendone(channel, "resume_timer", values)
