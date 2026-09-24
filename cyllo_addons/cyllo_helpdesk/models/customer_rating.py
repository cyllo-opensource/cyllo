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


class CustomerRating(models.Model):
    _inherit = "rating.rating"

    helpdesk_ticket_id = fields.Many2one(
        'helpdesk.ticket',
        string="Helpdesk Ticket",
        compute="_compute_helpdesk_ticket_id",
        store=True,
        readonly=True,
    )
    helpdesk_team_id = fields.Many2one(
        'helpdesk.team',
        string="Helpdesk Team",
        related='helpdesk_ticket_id.team_id',
        store=True,
        readonly=True,
    )
    helpdesk_user_id = fields.Many2one(
        'res.users',
        string="Assigned User",
        related='helpdesk_ticket_id.user_id',
        store=True,
        readonly=True,
    )
    helpdesk_stage_id = fields.Many2one(
        'helpdesk.stage',
        string="Ticket Stage",
        related='helpdesk_ticket_id.stage_id',
        store=True,
        readonly=True,
    )
    company_id= fields.Many2one('res.company', string="Company", related='helpdesk_ticket_id.company_id', store=True, readonly=True)

    @api.depends('res_model', 'res_id')
    def _compute_helpdesk_ticket_id(self):
        for rating in self:
            if rating.res_model == 'helpdesk.ticket' and rating.res_id:
                rating.helpdesk_ticket_id = rating.res_id
            else:
                rating.helpdesk_ticket_id = False

