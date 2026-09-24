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
from odoo import api, fields, models, _


class HelpDeskTicket(models.Model):
    _inherit = 'helpdesk.ticket'

    use_project = fields.Boolean(
        related='team_id.use_project', string="Use Project")
    project_id = fields.Many2one(
        'project.project', string='Project',
        related='team_id.project_id', readonly=False, store=True,
        help="Project associated with this ticket's team.")
    task_ids = fields.One2many(
        'project.task', 'helpdesk_ticket_id', string='Tasks')
    task_count = fields.Integer(compute='_compute_task_count')

    @api.depends('task_ids')
    def _compute_task_count(self):
        for ticket in self:
            ticket.task_count = len(ticket.task_ids)

    def action_create_task(self):
        """Open a pre-filled project task form linked to this ticket."""
        self.ensure_one()
        action = {
            'name': _('Create Task'),
            'type': 'ir.actions.act_window',
            'res_model': 'project.task',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_name': self.name,
                'default_helpdesk_ticket_id': self.id,
                'default_project_id': self.project_id.id if self.project_id else False,
                'default_partner_id': self.customer_id.id if self.customer_id else False,
                'default_description': self.description or '',
                'default_user_ids': [self.user_id.id] if self.user_id else [],
            },
        }
        self._message_log(body=_("Project task creation initiated."))
        return action

    def action_view_tasks(self):
        """Open a list/form view of all tasks linked to this ticket."""
        self.ensure_one()
        action = {
            'name': _('Tasks'),
            'type': 'ir.actions.act_window',
            'res_model': 'project.task',
            'view_mode': 'list,form',
            'domain': [('helpdesk_ticket_id', '=', self.id)],
            'context': {
                'default_helpdesk_ticket_id': self.id,
                'default_project_id': self.project_id.id if self.project_id else False,
                'default_partner_id': self.customer_id.id if self.customer_id else False,
            },
        }
        if self.task_count == 1:
            action['view_mode'] = 'form'
            action['res_id'] = self.task_ids.id
        return action
