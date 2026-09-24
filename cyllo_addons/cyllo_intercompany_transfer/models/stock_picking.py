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


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    intercompany_waiting = fields.Boolean(
        default=False,
        copy=False
    )

    def action_assign(self):
        """
        Override action_assign to prevent reservation for receipts
        that are waiting for intercompany synchronization.
        """
        waiting_pickings = self.filtered(
            lambda p:
            p.picking_type_code == 'incoming'
            and p.purchase_id
            and p.purchase_id.intercompany_sale_order_id
        )
        normal_pickings = self - waiting_pickings
        if not normal_pickings:
            return True
        return super(StockPicking, normal_pickings).action_assign()

    def button_validate(self):
        """
        Override button_validate to trigger intercompany receipt synchronization
        when an outgoing delivery is validated.
        """
        res = super().button_validate()
        sync_moves = self.env['ir.config_parameter'].sudo().get_param(
            'cyllo_intercompany_transfer.synchronize_stock_moves'
        )
        if sync_moves:
            self._sync_intercompany_receipt()
        return res

    def _sync_intercompany_receipt(self):
        """
        Synchronize validated outgoing delivery quantities with intercompany receipts.

        This method ensures that when a delivery order is validated, the corresponding
        incoming receipt in the customer company is updated accordingly.

        It performs the following operations:
        - Filters only outgoing validated deliveries
        - Identifies related Sale Order and intercompany Purchase Order
        - Finds matching incoming receipts in waiting state
        - Aggregates delivered quantities per product
        - Updates receipt stock moves based on partial or full delivery
        - Marks receipt as processed to avoid duplicate synchronization
        """

        for delivery in self:
            if delivery.picking_type_code != 'outgoing':
                continue
            if delivery.state != 'done':
                continue
            sale_order = delivery.sudo().sale_id
            if not sale_order:
                continue

            purchase_order = sale_order.sudo().intercompany_purchase_order_id
            if not purchase_order:
                continue
            receipts = self.env['stock.picking'].sudo().search([
                ('purchase_id', '=', purchase_order.id),
                ('picking_type_code', '=', 'incoming'),
                ('state', 'not in', ['done', 'cancel']),
                ('intercompany_waiting', '=', True)
            ])

            for receipt in receipts:
                qty_map = {}
                for move in delivery.move_ids:
                    for line in move.move_line_ids:
                        # qty = getattr(line, 'qty_done', getattr(line, 'quantity', 0.0))
                        qty = line.quantity or 0.0
                        if qty > 0:
                            qty_map[move.product_id.id] = qty_map.get(
                                move.product_id.id, 0.0
                            ) + qty
                if not qty_map:
                    continue
                for receipt_move in receipt.move_ids:
                    qty = qty_map.get(receipt_move.product_id.id, 0.0)
                    if qty > 0:
                        if receipt_move.intercompany_original_qty > qty:
                            receipt_move.write({
                                'quantity': qty,
                                'intercompany_original_qty': receipt_move.intercompany_original_qty - qty
                            })
                        else:
                            receipt_move.write({
                                'product_uom_qty': receipt_move.intercompany_original_qty,
                                'quantity' : qty,
                                'intercompany_original_qty': 0.0
                            })

                receipt.write({
                    'intercompany_waiting': False
                })
                receipt._message_log(
                    body="Intercompany delivery validated. Receipt updated and ready."
                )
