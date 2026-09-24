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
from odoo import fields, models, _


class HelpDeskTeam(models.Model):
    _inherit = 'helpdesk.team'

    return_count = fields.Integer(compute='_compute_return_count', string="Returns")

    def _compute_return_count(self):
        for team in self:
            team.return_count = self.env['stock.picking'].search_count([
                ('helpdesk_ticket_id.team_id', '=', team.id),
                ('picking_type_code', '=', 'incoming'),
            ])

    def action_view_team_returns(self):
        self.ensure_one()
        return {
            'name': _('Returns'),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'view_mode': 'tree,form',
            'domain': [('helpdesk_ticket_id.team_id', '=', self.id), ('picking_type_code', '=', 'incoming')],
            'target': 'current',
        }
