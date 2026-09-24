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


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    intercompany_generated = fields.Boolean(
        default=False,
        copy=False,
    )

    intercompany_sale_order_id = fields.Many2one(
        'sale.order',
        copy=False,
    )

    def button_confirm(self):
        """
        Confirm the Purchase Order and prepare intercompany processing.

        For intercompany Purchase Orders, incoming receipts are placed in a
        waiting state with zero available quantity until the corresponding
        supplier delivery is validated. Optionally creates a matching
        intercompany Sale Order based on configuration settings.
        """
        res = super().button_confirm()


        create_so = self.env['ir.config_parameter'].sudo().get_param(
            'cyllo_intercompany_transfer.create_sale_orders'
        )

        if not create_so:
            return res

        if self._is_intercompany_purchase():
            for po in self:

                receipts = po.picking_ids.filtered(
                    lambda p: p.picking_type_code == 'incoming'
                    and p.state not in ('done', 'cancel')
                )
                for receipt in receipts:
                    receipt.write({
                        'intercompany_waiting': True,
                        'state': 'confirmed',
                    })
                    for move in receipt.move_ids:
                        move.write({
                            'intercompany_original_qty': move.product_uom_qty,
                            'quantity': 0.0,
                        })
                if po.intercompany_generated or po.intercompany_sale_order_id:
                    continue
                po._create_intercompany_sale_order()

        return res

    def _is_intercompany_purchase(self):
        """
        Determine whether the Purchase Order vendor is another company
        within the same database and therefore qualifies as an
        intercompany transaction.
        """
        self.ensure_one()
        supplier_company = self.env['res.company'].search([
            ('partner_id', '=', self.partner_id.id)
        ], limit=1)

        return bool(supplier_company)

    def _create_intercompany_sale_order(self):
        """
        Create a corresponding Sale Order in the supplier company for an
        intercompany Purchase Order and establish links between both
        documents for synchronization and traceability.
        """
        self.ensure_one()
        supplier_company = self.env['res.company'].search([
            ('partner_id', '=', self.partner_id.id)
        ], limit=1)

        if not supplier_company:
            return False
        so = self.env['sale.order'].with_company(supplier_company).create({
            'partner_id': self.company_id.partner_id.id,
            'company_id': supplier_company.id,
            'origin': self.name,
            'intercompany_generated': True,
        })
        for line in self.order_line:
            self.env['sale.order.line'].with_company(supplier_company).create({
                'order_id': so.id,
                'product_id': line.product_id.id,
                'product_uom_qty': line.product_qty,
                'price_unit': line.price_unit,
                'name': line.name,
            })
        so.intercompany_purchase_order_id = self.id
        self.intercompany_sale_order_id = so.id
        return so
