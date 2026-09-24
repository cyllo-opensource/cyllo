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
from odoo.exceptions import UserError

class HelpdeskTicketMergeWizard(models.TransientModel):
    _name = 'helpdesk.ticket.merge.wizard'
    _description = 'Merge Helpdesk Tickets'

    ticket_ids = fields.Many2many('helpdesk.ticket', string='Tickets to Merge', required=True)
    dst_ticket_id = fields.Many2one('helpdesk.ticket', string='Destination Ticket', required=True, help="Resulting ticket after merge")

    @api.model
    def default_get(self, fields_list):
        res = super(HelpdeskTicketMergeWizard, self).default_get(fields_list)
        active_ids = self.env.context.get('active_ids')
        if active_ids:
            res['ticket_ids'] = [(6, 0, active_ids)]
            res['dst_ticket_id'] = active_ids[0]
        return res

    def action_merge(self):
        self.ensure_one()
        if len(self.ticket_ids) < 2:
            raise UserError(_("Please select at least two tickets to merge."))
        destination = self.dst_ticket_id
        source_tickets = self.ticket_ids - destination
        for ticket in source_tickets:
            messages = self.env['mail.message'].search([
                ('res_id', '=', ticket.id),
                ('model', '=', 'helpdesk.ticket')
            ])
            messages.write({'res_id': destination.id})
            attachments = self.env['ir.attachment'].search([
                ('res_id', '=', ticket.id),
                ('res_model', '=', 'helpdesk.ticket')
            ])
            attachments.write({'res_id': destination.id})
            ticket.child_ids.write({'parent_id': destination.id})
            if ticket.dependency_ids:
                destination.dependency_ids = [(4, dep.id) for dep in ticket.dependency_ids]
            destination.message_post(
                body=_("Ticket %s has been merged into this ticket.") % ticket.ticket
            )
            ticket.message_post(
                body=_("This ticket has been merged into %s.") % destination.ticket
            )
            canceled_stage = self.env.ref(
                'cyllo_helpdesk.canceled_ticket', raise_if_not_found=False
            )
            if canceled_stage:
                ticket.write({'stage_id': canceled_stage.id})

        return {'type': 'ir.actions.act_window_close'}
