# -*- coding: utf-8 -*-
#############################################################################
#
#    Cyllo Pvt. Ltd.
#
#    Copyright (C) 2025-TODAY Cyllo(<https://www.cyllo.com>)
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
from odoo import _, api, fields, models


class RepairOrderWizard(models.TransientModel):
    """Wizard for creating repair order from support ticket"""
    _name = 'repair.order.wizard'
    _description = 'Repair order Wizard'

    ticket_id = fields.Many2one('support.service.ticket',
                                string="Support Service Ticket")
    sale_order_id = fields.Many2one('sale.order', help="Sale order",
                                    required=True)
    product_ids = fields.Many2many('product.product',
                                   compute="_compute_product_ids")
    product_id = fields.Many2one('product.product', string="Product to Repair",
                                 domain="[('id', 'in', product_ids)]",
                                 required=True)
    partner_id = fields.Many2one('res.partner', string="Customer")
    internal_notes = fields.Html(help="Description about the issue or question")

    @api.depends('sale_order_id')
    def _compute_product_ids(self):
        for rec in self:
            rec.product_ids = rec.sale_order_id.order_line.mapped(
                'product_id').ids

    def action_confirm(self):
        """Action for creating repair order for the selected product"""
        self.env['repair.order'].create({
            'partner_id': self.partner_id.id,
            'internal_notes': self.internal_notes,
            'ticket_id': self.ticket_id.id,
            'product_id': self.product_id.id,
            'picking_type_id': self.env['stock.warehouse'].search(
                [('company_id', '=', self.env.company.id)],
                limit=1).repair_type_id.id, })
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'title': _("Order created"),
                'message': 'The repair order was created successfully for the '
                           'product ' + self.product_id.name if self.product_id
                else 'The repair order was created successfully.',
                'next': {
                    'type': 'ir.actions.act_window_close'
                },
            }
        }
