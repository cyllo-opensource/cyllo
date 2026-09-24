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

    repair_ids = fields.One2many('repair.order', 'helpdesk_ticket_id',
                                 string='Repair Orders')
    repair_count = fields.Integer(compute='_compute_repair_count')
    sale_order_id = fields.Many2one(
        'sale.order',
        string='Sale Order',
        help='Sale order associated with this helpdesk ticket',
    )
    sale_order_line_id = fields.Many2one(
        'sale.order.line',
        string='Sale Order Line',
        domain="[('order_id', '=', sale_order_id)]",
        help='Specific sale order line for this repair',
    )

    @api.depends('repair_ids')
    def _compute_repair_count(self):
        for ticket in self:
            ticket.repair_count = len(ticket.sudo().repair_ids)

    def action_create_repair(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "repair.action_repair_order_tree")
        action['res_model'] = 'repair.order'
        action['view_mode'] = 'form'
        action['views'] = [
            (self.env.ref('repair.view_repair_order_form').id, 'form')]
        action['target'] = 'current'
        action['context'] = {
            'default_partner_id': self.customer_id.id if self.customer_id else False,
            'default_ticket_id': self.id,
            'default_helpdesk_ticket_id': self.id,
            'default_sale_order_id': self.sale_order_id.id if self.sale_order_id else False,
            'default_sale_order_line_id': self.sale_order_line_id.id if self.sale_order_line_id else False,
            'default_product_id': self.sale_order_line_id.product_id.id if self.sale_order_line_id else False,
            'default_under_warranty': (
                self.warranty_status == 'under_warranty'
                if hasattr(self, 'warranty_status') and self.warranty_status
                else False
            ),
        }
        self._message_log(body=_("Repair Order creation initiated."))
        return action

    def action_view_repairs(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "repair.action_repair_order_tree")
        action['view_mode'] = 'list,form'
        action['domain'] = [('helpdesk_ticket_id', '=', self.id)]
        return action
