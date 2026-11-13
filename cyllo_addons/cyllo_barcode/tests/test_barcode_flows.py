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
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestBarcodeFlows(TransactionCase):
    """End-to-end scan flows on receipts, deliveries and internal transfers."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.BM = cls.env['barcode.management']
        cls.wh = cls.env['stock.warehouse'].search([], limit=1)
        cls.stock_loc = cls.wh.lot_stock_id
        cls.loc_a = cls.env['stock.location'].create({
            'name': 'Bin A', 'usage': 'internal', 'barcode': 'BIN-A',
            'location_id': cls.stock_loc.id})
        cls.loc_b = cls.env['stock.location'].create({
            'name': 'Bin B', 'usage': 'internal', 'barcode': 'BIN-B',
            'location_id': cls.stock_loc.id})
        Product = cls.env['product.product']
        cls.p_none = Product.create({'name': 'Plain', 'type': 'product', 'barcode': 'P-NONE'})
        cls.p_lot = Product.create({'name': 'Lotted', 'type': 'product',
                                    'tracking': 'lot', 'barcode': 'P-LOT'})
        cls.p_serial = Product.create({'name': 'Serialed', 'type': 'product',
                                       'tracking': 'serial', 'barcode': 'P-SER'})

    def _picking(self, code):
        ptype = self.env['stock.picking.type'].with_context(active_test=False).search(
            [('code', '=', code), ('warehouse_id', '=', self.wh.id)], limit=1)
        ptype.active = True
        src = {'incoming': 'stock.stock_location_suppliers'}.get(code)
        dst = {'outgoing': 'stock.stock_location_customers'}.get(code)
        return self.env['stock.picking'].create({
            'picking_type_id': ptype.id,
            'location_id': ptype.default_location_src_id.id or (
                self.env.ref(src).id if src else self.stock_loc.id),
            'location_dest_id': ptype.default_location_dest_id.id or (
                self.env.ref(dst).id if dst else self.stock_loc.id),
            'with_barcode': True,
        })

    def _scan(self, picking, product, barcode=''):
        self.BM.add_stock_move_line(
            picking.id, res_model='product.product', data=[{'id': product.id}],
            barcode=barcode)

    # -- scanning quantities ------------------------------------------------
    def test_repeated_scan_increments_quantity(self):
        picking = self._picking('incoming')
        for _i in range(3):
            self._scan(picking, self.p_none)
        line = picking.move_line_ids
        self.assertEqual(len(line), 1)
        self.assertEqual(line.quantity, 3)
        self.assertTrue(line.is_barcode_scanned)

    def test_scan_two_products_creates_two_moves(self):
        picking = self._picking('incoming')
        self._scan(picking, self.p_none)
        self._scan(picking, self.p_lot, 'LOT-1')
        self.assertEqual(picking.move_ids_without_package.product_id,
                         self.p_none | self.p_lot)

    def test_lot_scan_same_lot_increments(self):
        picking = self._picking('incoming')
        self.BM._handle_barcode_scan(picking, 'LOT-1', self.p_lot)
        self.BM._handle_barcode_scan(picking, 'LOT-1', self.p_lot)
        lines = picking.move_line_ids
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines.quantity, 2)
        self.assertEqual(lines.lot_name, 'LOT-1')

    def test_lot_scan_different_lots_create_lines(self):
        picking = self._picking('incoming')
        self.BM._handle_barcode_scan(picking, 'LOT-1', self.p_lot)
        self.BM._handle_barcode_scan(picking, 'LOT-2', self.p_lot)
        self.assertEqual(sorted(picking.move_line_ids.mapped('lot_name')),
                         ['LOT-1', 'LOT-2'])

    def test_serial_scan_one_line_per_serial(self):
        picking = self._picking('incoming')
        self.BM._handle_barcode_scan(picking, 'S1', self.p_serial)
        self.BM._handle_barcode_scan(picking, 'S2', self.p_serial)
        self.assertEqual(len(picking.move_line_ids), 2)
        self.assertEqual(set(picking.move_line_ids.mapped('quantity')), {1})

    # -- lots ---------------------------------------------------------------
    def test_create_lot(self):
        lot = self.BM.create_lot('NEW-LOT', self.p_lot.id)
        self.assertEqual(lot.name, 'NEW-LOT')
        self.assertEqual(lot.product_id, self.p_lot)

    def test_assign_lot_number_to_scanned_line(self):
        picking = self._picking('incoming')
        self._scan(picking, self.p_lot)
        lot = self.BM.create_lot('L-ASSIGN', self.p_lot.id)
        self.BM.assign_lot_number(picking, lot, self.p_lot.id)
        self.assertEqual(picking.move_line_ids.lot_id, lot)
        self.assertEqual(picking.move_line_ids.lot_name, 'L-ASSIGN')

    def test_assign_lot_number_lot_product_can_repeat(self):
        """The duplicate check only applies to serial tracked products."""
        picking = self._picking('incoming')
        self._scan(picking, self.p_lot)
        self._scan(picking, self.p_lot)
        lot = self.BM.create_lot('L-REP', self.p_lot.id)
        self.BM.assign_lot_number(picking, lot, self.p_lot.id)
        self.BM.assign_lot_number(picking, lot, self.p_lot.id)

    # -- packages -----------------------------------------------------------
    def test_assign_package(self):
        picking = self._picking('incoming')
        self._scan(picking, self.p_none)
        pack = self.env['stock.quant.package'].create({'name': 'PACK-1'})
        self.BM.assign_package_move_line(
            picking.id, data=[{'id': pack.id}], res_model='stock.quant.package')
        self.assertEqual(picking.move_line_ids.result_package_id, pack)

    def test_assign_package_without_scanned_product_fails(self):
        picking = self._picking('incoming')
        pack = self.env['stock.quant.package'].create({'name': 'PACK-2'})
        with self.assertRaises(UserError):
            self.BM.assign_package_move_line(
                picking.id, data=[{'id': pack.id}], res_model='stock.quant.package')

    def test_assign_package_cannot_be_reused(self):
        picking = self._picking('incoming')
        self._scan(picking, self.p_none)
        pack = self.env['stock.quant.package'].create({'name': 'PACK-3'})
        data = [{'id': pack.id}]
        self.BM.assign_package_move_line(picking.id, data=data, res_model='stock.quant.package')
        with self.assertRaises(UserError):
            self.BM.assign_package_move_line(picking.id, data=data, res_model='stock.quant.package')

    def test_assign_package_batch(self):
        p1, p2 = self._picking('incoming'), self._picking('incoming')
        self._scan(p1, self.p_none)
        self._scan(p2, self.p_none)
        pack = self.env['stock.quant.package'].create({'name': 'PACK-B'})
        self.BM.assign_package_move_line_batch(
            [p1.id, p2.id], data=[{'id': pack.id}], res_model='stock.quant.package')
        self.assertEqual((p1 | p2).move_line_ids.result_package_id, pack)

    # -- locations ----------------------------------------------------------
    def test_outgoing_source_location_scan(self):
        picking = self._picking('outgoing')
        self._scan(picking, self.p_none)
        self.BM.add_stock_location(
            picking.id, picking_type='outgoing',
            data=[{'id': self.loc_a.id}], res_model='stock.location')
        self.assertEqual(picking.move_line_ids.location_id, self.loc_a)

    def test_location_batch(self):
        p1, p2 = self._picking('incoming'), self._picking('incoming')
        self._scan(p1, self.p_none)
        self._scan(p2, self.p_none)
        self.BM.add_stock_location_batch(
            [p1.id, p2.id], picking_type='incoming',
            data=[{'id': self.loc_b.id}], res_model='stock.location')
        self.assertEqual((p1 | p2).location_dest_id, self.loc_b)

    # -- removal / increment ------------------------------------------------
    def test_remove_move_line_resets_recent_scan(self):
        picking = self._picking('incoming')
        self._scan(picking, self.p_none)
        line = picking.move_line_ids
        self.BM.action_remove_move_line(picking.id, line.id, 'stock.move.line')
        self.assertFalse(line.exists())
        self.assertFalse(picking.barcode_recent_scan)
        self.assertFalse(picking.last_scanned_product)

    def test_remove_move(self):
        picking = self._picking('incoming')
        self._scan(picking, self.p_none)
        move = picking.move_ids_without_package
        self.BM.action_remove_move_line(picking.id, move.id, 'stock.move')
        self.assertFalse(move.exists())

    def test_remove_ignores_unknown_model(self):
        picking = self._picking('incoming')
        self._scan(picking, self.p_none)
        self.BM.action_remove_move_line(picking.id, picking.move_line_ids.id, 'res.partner')
        self.assertTrue(picking.move_line_ids)

    def test_add_move_line_by_one(self):
        picking = self._picking('incoming')
        self._scan(picking, self.p_none)
        move = picking.move_ids_without_package
        self.BM.add_move_line_by_one(move.id)
        self.assertEqual(sum(move.move_line_ids.mapped('quantity')), 2)

    # -- recent scan routing ------------------------------------------------
    def test_recent_scan_on_batch_record(self):
        picking = self._picking('internal')
        batch = self.env['stock.picking.batch'].create({
            'picking_type_id': picking.picking_type_id.id})
        self.BM.pre_process_assign_recent_scan(
            picking, 'product.product', 'none', self.p_none.id,
            rec_model='stock.picking.batch', rec_model_id=batch.id)
        self.assertEqual(batch.barcode_recent_scan, 'product.product')
        self.assertFalse(picking.barcode_recent_scan)

    # -- search -------------------------------------------------------------
    def test_search_picking_by_name(self):
        picking = self._picking('incoming')
        res = self.BM.search_barcode_in_models(picking.name, picking.id)
        self.assertEqual(res['res_model'], 'stock.picking')

    def test_search_reports_picking_type(self):
        picking = self._picking('outgoing')
        res = self.BM.search_barcode_in_models('P-NONE', picking.id)
        self.assertEqual(res['picking_type'], 'outgoing')

    def test_search_in_batch_flags_product(self):
        p1 = self._picking('internal')
        self._scan(p1, self.p_none)
        batch = self.env['stock.picking.batch'].create({
            'picking_type_id': p1.picking_type_id.id, 'picking_ids': [(4, p1.id)]})
        res = self.BM.search_barcode_in_models('P-NONE', p1.id, batch.id)
        self.assertTrue(res['product_exist'])
        self.assertEqual(res['exist_picking_ids'], [p1.id])
        res = self.BM.search_barcode_in_models('P-LOT', p1.id, batch.id)
        self.assertFalse(res['product_exist'])

    def test_search_location_requires_multi_location_group(self):
        user = self.env['res.users'].create({
            'name': 'Plain Stock User', 'login': 'bc_plain_user',
            'groups_id': [(6, 0, [self.env.ref('base.group_user').id,
                                  self.env.ref('stock.group_stock_user').id])]})
        user.groups_id -= self.env.ref('stock.group_stock_multi_locations')
        models = self.BM.with_user(user).return_barcode_models()
        self.assertNotIn('stock.location', models)
        self.assertIn('product.product', models)

    # -- full receipt -------------------------------------------------------
    def test_validate_receipt_updates_stock(self):
        picking = self._picking('incoming')
        for _i in range(4):
            self._scan(picking, self.p_none)
        picking.with_context(skip_backorder=True, skip_sms=True).button_validate()
        self.assertEqual(picking.state, 'done')
        self.p_none.invalidate_recordset()
        self.assertEqual(self.p_none.qty_available, 4)
