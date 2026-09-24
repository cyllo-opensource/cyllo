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

    sale_order_id = fields.Many2one(
        'sale.order',
        string="Sale Order",
        help="Sale Order linked to this ticket (filtered by the selected customer).",
    )
    sale_order_line_id = fields.Many2one(
        'sale.order.line',
        string="Order Line",
        domain="[('order_id', '=', sale_order_id)]",
    )
    sale_order_ids = fields.One2many(
        'sale.order',
        'helpdesk_ticket_id',
        string="Sale Orders",
    )
    sale_order_count = fields.Integer(
        compute='_compute_sale_order_count',
        string="Sales Order Count",
    )
    customer_sale_order_count = fields.Integer(
        compute='_compute_customer_sale_order_count',
        string="Customer Sales Count",
    )

    @api.depends('sale_order_ids')
    def _compute_sale_order_count(self):
        for ticket in self:
            ticket.sale_order_count = len(ticket.sale_order_ids)

    @api.depends('customer_id')
    def _compute_customer_sale_order_count(self):
        for ticket in self:
            if not ticket.customer_id:
                ticket.customer_sale_order_count = 0
                continue
            commercial_partner = ticket.customer_id.commercial_partner_id
            ticket.customer_sale_order_count = self.env['sale.order'].sudo().search_count(
                [('partner_id', 'child_of', commercial_partner.id)])

    def action_create_sale_order(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Sale Order',
            'res_model': 'sale.order',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_partner_id': self.customer_id.id,
                'default_helpdesk_ticket_id': self.id,
            },
        }

    def action_view_sale_orders(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("sale.action_orders")
        action['domain'] = [('helpdesk_ticket_id', '=', self.id)]
        return action

    def action_view_customer_sale_orders(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("sale.action_orders")
        action['domain'] = [('partner_id', 'child_of', self.customer_id.commercial_partner_id.id)]
        action['context'] = {'create': False, 'edit': False}
        return action

    @api.onchange('customer_id')
    def _onchange_customer_id_sale(self):
        """Set sale order domain and clear SO if customer changes."""
        if not self.customer_id:
            self.sale_order_id = False
            self.sale_order_line_id = False
            return {'domain': {'sale_order_id': [('id', '=', False)]}}
        
        commercial = self.customer_id.commercial_partner_id
        domain = [
            ('partner_id', 'child_of', commercial.id),
            ('state', 'in', ['sale', 'done']),
        ]
        if self.sale_order_id and self.sale_order_id.partner_id.commercial_partner_id != commercial:
            self.sale_order_id = False
            self.sale_order_line_id = False
        return {'domain': {'sale_order_id': domain}}
