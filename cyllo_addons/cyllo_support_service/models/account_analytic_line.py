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
from odoo import api, fields, models
from odoo.osv import expression


class AccountAnalyticLine(models.Model):
    """ Class to add timesheet for the employee """
    _inherit = "account.analytic.line"

    def _domain_project_id(self):
        """To set up domain for project_id field"""
        domain = [('allow_timesheets', '=', True)]
        if not self.user_has_groups('hr_timesheet.group_timesheet_manager'):
            return expression.AND(
                [domain, ['|', ('privacy_visibility', '!=', 'followers'),
                          ('message_partner_ids', 'in',
                           [self.env.user.partner_id.id])]])
        return domain

    ticket_id = fields.Many2one('support.service.ticket', string="Ticket Id",
                                help="Support Service ticket Id")
    project_id = fields.Many2one('project.project', 'Project',
                                 domain=_domain_project_id, index=True,
                                 compute='_compute_project_id', store=True,
                                 readonly=False)

    @api.depends('task_id')
    def _compute_project_id(self):
        """
        Compute and set the 'project_id' based on the related task and ticket.

        This method is triggered by changes in the 'task_id' and 'ticket_id' fields. For each record,
        it checks if the 'task_id' has a project, and if not, it continues to the next record.
        If the 'task_id' has a project different from the current 'project_id', it updates 'project_id'
        with the project of the task.

        Additionally, if the record has a 'ticket_id' and the 'project_id' is not set, it sets 'project_id'
        based on the 'team_id' of the ticket.

        :return: None
        """
        for line in self:
            if not line.task_id.project_id or line.project_id == line.task_id.project_id:
                continue
            line.project_id = line.task_id.project_id
        if self.ticket_id and not self.project_id:
            self.project_id = self.ticket_id.team_id.project_id.id
