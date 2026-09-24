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


class HelpDeskSLAPolicy(models.Model):
    _name = "helpdesk.sla"
    _description = "HelpDesk SLA Policy"

    name = fields.Char(string="Name", help="Name for SLA policy")
    description = fields.Html(string="Description",
                              help="Description for SLA policy")
    team_ids = fields.Many2many('helpdesk.team', string="Teams",required=1,
                               domain="[('use_sla', '=', True)]",
                               help="Helpdesk teams")
    category_ids = fields.Many2many('helpdesk.category', string="Category",
                                    help=" Specific ticket categories that trigger this SLA.")
    tag_ids = fields.Many2many('helpdesk.tag', string="Tag",
                               help="Specific tags that trigger this SLA.")
    customer_ids = fields.Many2many('res.partner', string="Customer",
                                    help="Customers who affect this SLA policy")
    target_stage = fields.Many2one('helpdesk.stage', default=lambda self: self.env.ref(
                                   'cyllo_helpdesk.solved_ticket').id, string="Target stage", required=True,
                                   help="The stage in which the ticket reach to satisfy this SLA")
    within_hour = fields.Float(string="Within",
                               help="Maximum number of working hours that a ticket should take to reach the target stage")
    excluded_stage_ids = fields.Many2many('helpdesk.stage', string="Excluding Stages",
                                          help="Stages to be excluded from SLA calculation")
    ticket_count = fields.Integer(compute="_compute_ticket_count", string="Tickets")
    company_id= fields.Many2one("res.company", string="Company", default=lambda self: self.env.company)

    def _compute_ticket_count(self):
        for record in self:
            record.ticket_count = self.env['helpdesk.ticket'].search_count([('sla_ids', 'in', record.ids)])

    def action_view_sla_tickets(self):
        self.ensure_one()
        return {
            'name': _('Tickets'),
            'type': 'ir.actions.act_window',
            'res_model': 'helpdesk.ticket',
            'view_mode': 'tree,form',
            'domain': [('sla_ids', 'in', self.ids)],
            'target': 'current',
        }

    @api.constrains('team_ids')
    def _check_team_ids(self):
        for policy in self:
            for team in policy.team_ids:
                if not team.use_sla:
                    raise models.ValidationError(_(
                        "The selected team '%s' does not have SLA enabled. "
                        "Please enable 'Use SLA' on the team first."
                    ) % team.name)

