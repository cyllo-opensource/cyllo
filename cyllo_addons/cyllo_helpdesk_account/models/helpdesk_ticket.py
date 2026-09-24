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

    refund_ids = fields.One2many(
        'account.move',
        'helpdesk_ticket_id',
        string="Refund/Credit Notes",
        domain=[('move_type', '=', 'out_refund')],
    )
    refund_count = fields.Integer(
        compute='_compute_refund_count',
        string="Refund Count",
    )

    @api.depends('refund_ids')
    def _compute_refund_count(self):
        for ticket in self:
            ticket.refund_count = len(ticket.refund_ids)

    def action_view_refunds(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Credit Notes'),
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'domain': [
                ('helpdesk_ticket_id', '=', self.id),
                ('move_type', '=', 'out_refund'),
            ],
            'target': 'current',
        }

    def action_create_refund(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create Refund'),
            'res_model': 'helpdesk.refund.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_ticket_id': self.id,
                'default_customer_id': self.customer_id.id,
            }
        }
