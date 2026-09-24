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


class HelpdeskTicketReturnWizard(models.TransientModel):
    _name = 'helpdesk.ticket.return.wizard'
    _description = 'Helpdesk Ticket Return Wizard'

    ticket_id = fields.Many2one('helpdesk.ticket', string='Ticket', readonly=True)
    sale_order_id = fields.Many2one('sale.order', string='Sale Order', readonly=True)
    picking_id = fields.Many2one('stock.picking', string='Delivery Order', required=True)

    def action_confirm(self):
        self.ensure_one()
        action = self.env.ref('stock.act_stock_return_picking').read()[0]
        action['context'] = {
            'active_id': self.picking_id.id,
            'active_ids': [self.picking_id.id],
            'active_model': 'stock.picking',
            'default_helpdesk_ticket_id': self.ticket_id.id,
        }
        return action
