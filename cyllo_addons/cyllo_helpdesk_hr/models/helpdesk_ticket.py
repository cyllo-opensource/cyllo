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
from odoo import api, fields, models


class HelpDeskTicket(models.Model):
    _inherit = 'helpdesk.ticket'

    skill_ids = fields.Many2many('hr.skill', string='Required Skills')

    @api.onchange('team_id', 'skill_ids')
    def _onchange_team_id_assignment(self):
        super()._onchange_team_id_assignment()
        if self.team_id and self.team_id.assignment_method == 'skill' and self.team_id.member_ids:
            self._assign_by_skill(self.team_id.member_ids)

    def _assign_ticket(self):
        if self.team_id.assignment_method == 'skill' and self.skill_ids:
            self._assign_by_skill(self.team_id.member_ids)
        else:
            super()._assign_ticket()

    def _assign_by_skill(self, members):
        required_skill_ids = self.skill_ids.ids
        employees = self.env['hr.employee'].search([
            ('user_id', 'in', members.ids)
        ])
        member_data = []
        for emp in employees:
            emp_skill_ids = emp.employee_skill_ids.mapped('skill_id.id')
            match_count = len(set(emp_skill_ids) & set(required_skill_ids))
            ticket_count = self.env['helpdesk.ticket'].search_count([
                ('user_id', '=', emp.user_id.id),
                ('stage_id.is_closed', '=', False)
            ])
            member_data.append({
                'user_id': emp.user_id.id,
                'matches': match_count,
                'tickets': ticket_count
            })
        if member_data:
            best_candidates = sorted(member_data,
                                     key=lambda x: (-x['matches'],
                                                    x['tickets']))
            self.user_id = best_candidates[0]['user_id']
