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

from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    intercompany_generated = fields.Boolean(
        default=False,
        copy=False,
    )

    intercompany_purchase_order_id = fields.Many2one(
        'purchase.order',
        copy=False,
    )

    def action_confirm(self):
        """
        Confirm the Sale Order and optionally trigger intercompany purchase order creation.

        After the standard confirmation flow, this method checks system configuration
        parameters to determine whether intercompany transactions are enabled and
        whether purchase orders should be created automatically.

        If enabled, it generates a corresponding Purchase Order in the related
        customer company, unless it has already been generated.
        """
        res = super().action_confirm()
        create_po = self.env['ir.config_parameter'].sudo().get_param(
            'cyllo_intercompany_transfer.create_purchase_orders'
        )
        if not create_po:
            return res
        for so in self:
            if so.intercompany_generated or so.intercompany_purchase_order_id:
                continue
            so._create_intercompany_purchase_order()

        return res

    def _create_intercompany_purchase_order(self):
        """
        Create a Purchase Order in the customer company's environment based on this Sale Order.

        This method:
        - Identifies the company linked to the customer partner
        - Creates a Purchase Order in that company context
        - Mirrors all Sale Order lines into Purchase Order lines
        - Links both documents together for traceability
        """
        self.ensure_one()
        customer_company = self.env['res.company'].search([
            ('partner_id', '=', self.partner_id.id)
        ], limit=1)
        if not customer_company:
            return False
        po = self.env['purchase.order'].with_company(customer_company).create({
            'partner_id': self.company_id.partner_id.id,
            'company_id': customer_company.id,
            'origin': self.name,
            'intercompany_generated': True,
        })
        for line in self.order_line:
            self.env['purchase.order.line'].with_company(customer_company).create({
                'order_id': po.id,
                'product_id': line.product_id.id,
                'product_qty': line.product_uom_qty,
                'price_unit': line.price_unit,
                'name': line.name,
            })
        po.intercompany_sale_order_id = self.id
        self.intercompany_purchase_order_id = po.id

        return po
