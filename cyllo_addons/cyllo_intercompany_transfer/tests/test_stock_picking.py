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

from odoo.tests import tagged

from .common import IntercompanyCommon


@tagged('post_install', '-at_install')
class TestStockPicking(IntercompanyCommon):

    def setUp(self):
        super().setUp()
        self._set_params(
            create_purchase_orders=True,
            create_sale_orders=True,
            synchronize_stock_moves=True,
        )

    def _confirmed_flow(self, qty=10.0):
        """SO in A confirmed -> PO in B -> PO confirmed (receipt on hold)."""
        so = self._create_so(self.partner_b, qty=qty)
        so.action_confirm()
        po = so.intercompany_purchase_order_id
        po.with_company(self.company_b).button_confirm()
        receipt = po.picking_ids.filtered(
            lambda p: p.picking_type_code == 'incoming')
        delivery = so.picking_ids.filtered(
            lambda p: p.picking_type_code == 'outgoing')
        return so, po, delivery, receipt

    def _deliver(self, delivery, qty):
        delivery.move_ids.write({'quantity': qty, 'picked': True})
        return delivery.with_context(
            skip_backorder=True, picking_ids_not_to_backorder=delivery.ids,
        ).button_validate()

    def test_intercompany_waiting_default(self):
        self.assertFalse(self.env['stock.picking'].new({}).intercompany_waiting)

    def test_receipt_on_hold_after_po_confirmation(self):
        _so, _po, delivery, receipt = self._confirmed_flow(10)
        self.assertTrue(delivery)
        self.assertTrue(receipt.intercompany_waiting)
        self.assertEqual(receipt.move_ids.quantity, 0.0)
        self.assertEqual(receipt.move_ids.intercompany_original_qty, 10)

    def test_action_assign_skips_intercompany_receipt(self):
        _so, _po, _delivery, receipt = self._confirmed_flow(10)
        receipt.action_assign()
        self.assertEqual(receipt.move_ids.quantity, 0.0)
        self.assertEqual(receipt.move_ids.state, 'confirmed')

    def test_full_delivery_updates_receipt(self):
        _so, _po, delivery, receipt = self._confirmed_flow(10)
        self._deliver(delivery, 10)
        self.assertEqual(delivery.state, 'done')
        self.assertEqual(receipt.move_ids.quantity, 10)
        self.assertEqual(receipt.move_ids.intercompany_original_qty, 0)
        self.assertEqual(receipt.move_ids.state, 'assigned')
        self.assertFalse(receipt.intercompany_waiting)

    def test_partial_delivery_updates_receipt_partially(self):
        _so, _po, delivery, receipt = self._confirmed_flow(10)
        self._deliver(delivery, 4)
        self.assertEqual(receipt.move_ids.quantity, 4)
        self.assertEqual(receipt.move_ids.intercompany_original_qty, 6)
        self.assertTrue(receipt.intercompany_waiting)

    def test_sync_disabled_leaves_receipt_untouched(self):
        self._set_params(synchronize_stock_moves=False)
        _so, _po, delivery, receipt = self._confirmed_flow(10)
        self._deliver(delivery, 10)
        self.assertEqual(delivery.state, 'done')
        self.assertEqual(receipt.move_ids.quantity, 0.0)
        self.assertTrue(receipt.intercompany_waiting)

    def test_sync_ignores_non_outgoing_and_not_done(self):
        _so, _po, delivery, receipt = self._confirmed_flow(10)
        # Not done yet: nothing happens.
        delivery._sync_intercompany_receipt()
        self.assertEqual(receipt.move_ids.quantity, 0.0)
        # Receipts are never a sync source.
        receipt._sync_intercompany_receipt()
        self.assertEqual(receipt.move_ids.quantity, 0.0)

    def test_delivery_without_intercompany_link_is_ignored(self):
        self._set_params(create_purchase_orders=False)
        so = self._create_so(self.external_partner, qty=3)
        so.action_confirm()
        delivery = so.picking_ids.filtered(
            lambda p: p.picking_type_code == 'outgoing')
        self._deliver(delivery, 3)
        self.assertEqual(delivery.state, 'done')

    def test_receipt_validation_creates_backorder_with_pending_qty(self):
        _so, _po, delivery, receipt = self._confirmed_flow(10)
        self._deliver(delivery, 4)
        receipt.move_ids.picked = True
        receipt.with_context(
            skip_backorder=True, picking_ids_not_to_backorder=[],
        ).button_validate()
        backorder = receipt.backorder_ids
        self.assertTrue(backorder)
        self.assertEqual(backorder.move_ids.product_uom_qty, 6)
        self.assertEqual(backorder.move_ids.intercompany_original_qty, 6)
        self.assertEqual(backorder.move_ids.quantity, 0.0)
        self.assertTrue(backorder.intercompany_waiting)
        self.assertFalse(receipt.intercompany_waiting)
        self.assertEqual(receipt.move_ids.intercompany_original_qty, 0)
