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


class HelpDeskTicket(models.Model):
    _inherit = 'helpdesk.ticket'

    picking_ids = fields.Many2many('stock.picking',
                                   string='Returns/Replacements')
    picking_count = fields.Integer(compute='_compute_picking_count')

    @api.depends('picking_ids')
    def _compute_picking_count(self):
        for ticket in self:
            ticket.picking_count = len(ticket.picking_ids)

    def action_create_return(self):
        self.ensure_one()
        if not self.sale_order_id:
            raise UserError(_("Please select a Sale Order first."))

        pickings = self.env['stock.picking'].search([
            ('sale_id', '=', self.sale_order_id.id),
            ('state', '=', 'done'),
            ('picking_type_code', '=', 'outgoing'),
        ])

        if not pickings:
            raise UserError(_("No completed delivery available for return."))

        if len(pickings) == 1:
            action = self.env["ir.actions.actions"]._for_xml_id('stock.act_stock_return_picking')
            action['context'] = {
                'active_id': pickings.id,
                'active_ids': [pickings.id],
                'active_model': 'stock.picking',
                'default_helpdesk_ticket_id': self.id,
            }
            self._message_log(body=_("Return process initiated."))
            return action

        self._message_log(body=_("Return process initiated."))
        return {
            'name': _('Select Delivery to Return'),
            'type': 'ir.actions.act_window',
            'res_model': 'helpdesk.ticket.return.wizard',
            'view_mode': 'form',
            'view_id': self.env.ref(
                'cyllo_helpdesk_stock.helpdesk_ticket_return_wizard_view_form').id,
            'target': 'new',
            'context': {
                'default_ticket_id': self.id,
                'default_sale_order_id': self.sale_order_id.id,
            }
        }

    def action_view_pickings(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "stock.action_picking_tree_all")
        action['view_mode'] = 'list,form'
        action['domain'] = [('id', 'in', self.picking_ids.ids)]
        return action
