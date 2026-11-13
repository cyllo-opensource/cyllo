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
from odoo.tests.common import HttpCase, tagged


@tagged('post_install', '-at_install')
class TestBarcodeController(HttpCase):
    """JSON routes used by the barcode client actions."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.wh = cls.env['stock.warehouse'].search([], limit=1)
        cls.location = cls.env['stock.location'].create({
            'name': 'Ctrl Bin', 'usage': 'internal', 'barcode': 'CTRL-BIN',
            'location_id': cls.wh.lot_stock_id.id})
        cls.product = cls.env['product.product'].create({
            'name': 'Ctrl Product', 'type': 'product', 'barcode': 'CTRL-P'})
        cls.ptype = cls.wh.in_type_id
        cls.env['stock.picking.type'].with_context(active_test=False).search(
            [('code', '=', 'internal')]).active = True
        cls.picking = cls.env['stock.picking'].create({
            'picking_type_id': cls.ptype.id,
            'location_id': cls.env.ref('stock.stock_location_suppliers').id,
            'location_dest_id': cls.ptype.default_location_dest_id.id,
            'with_barcode': True,
        })

    def setUp(self):
        super().setUp()
        self.authenticate('admin', 'admin')

    def _rpc(self, route, **params):
        return self.make_jsonrpc_request(route, params)

    def test_barcode_scanned_product(self):
        res = self._rpc('/barcode/barcode-scanned', barcode='CTRL-P',
                        picking_id=self.picking.id)
        self.assertFalse(res['is_error'])
        self.assertEqual(res['res_model'], 'product.product')

    def test_barcode_scanned_unknown(self):
        res = self._rpc('/barcode/barcode-scanned', barcode='NOPE-XYZ',
                        picking_id=self.picking.id)
        self.assertTrue(res['is_error'])

    def test_main_barcode_unknown(self):
        res = self._rpc('/barcode/main-barcode', code='NOPE-XYZ',
                        company_id=self.env.company.id)
        self.assertEqual(res, {'type': 'no_data'})

    def test_main_barcode_product(self):
        res = self._rpc('/barcode/main-barcode', code='CTRL-P',
                        company_id=self.env.company.id)
        self.assertEqual(res['type'], 'product')
        self.assertEqual(res['id'], self.product.id)

    def test_main_barcode_location_creates_internal_transfer(self):
        res = self._rpc('/barcode/main-barcode', code='CTRL-BIN',
                        company_id=self.env.company.id)
        self.assertEqual(res['type'], 'location')
        picking = self.env['stock.picking'].browse(res['stock_transfer_id'])
        self.assertEqual(picking.picking_type_id.code, 'internal')
        self.assertEqual(picking.location_id, self.location)
        self.assertTrue(picking.with_barcode)

    def test_main_barcode_operation_type_creates_picking(self):
        self.ptype.barcode = 'WH-IN-TEST'
        res = self._rpc('/barcode/main-barcode', code='WH-IN-TEST',
                        company_id=self.env.company.id)
        self.assertEqual(res['type'], 'operation_type')
        picking = self.env['stock.picking'].browse(res['stock_transfer_id'])
        self.assertEqual(picking.picking_type_id, self.ptype)

    def test_get_product_data_after_scan(self):
        self.env['barcode.management'].add_stock_move_line(
            self.picking.id, res_model='product.product',
            data=[{'id': self.product.id}], barcode='CTRL-P')
        res = self._rpc('/barcode-location/get-product-data', pick_id=self.picking.id)
        self.assertEqual(len(res), 1)

    def test_get_product_data_empty(self):
        res = self._rpc('/barcode-location/get-product-data', pick_id=self.picking.id)
        self.assertEqual(res, [])

    def test_confirm_validates_picking(self):
        self.env['barcode.management'].add_stock_move_line(
            self.picking.id, res_model='product.product',
            data=[{'id': self.product.id}], barcode='CTRL-P')
        self._rpc('/barcode-location/product-barcode-confirm', pick_id=self.picking.id)
        self.picking.invalidate_recordset()
        self.assertEqual(self.picking.state, 'done')

    def test_location_package_flags(self):
        res = self._rpc('/barcode-batch/location-package')
        self.assertEqual(set(res), {'package', 'location'})
        self.assertIsInstance(res['package'], bool)

    def test_inventory_command_unknown_returns_true(self):
        res = self._rpc('/inventory_commands', code='unknown', id=self.picking.id)
        self.assertTrue(res)

    def test_inventory_command_slip_returns_report_action(self):
        res = self._rpc('/inventory_commands', code='action_picking', id=self.picking.id)
        self.assertIn(res['type'], ('ir.actions.report', 'ir.actions.act_window'))

    def test_adjustment_data_only_barcode_quants(self):
        quant = self.env['stock.quant'].create({
            'product_id': self.product.id,
            'location_id': self.location.id,
            'inventory_quantity': 5,
        })
        res = self._rpc('/barcode-adjustment/get_adjustment_stock_data')
        self.assertNotIn(quant.id, [r['id'] for r in res])

    def test_adjustment_cancel_and_apply(self):
        quant = self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': self.product.id,
            'location_id': self.location.id,
            'inventory_quantity': 7,
        })
        self.assertTrue(self._rpc('/barcode-adjustment/cancel_stock_quant',
                                  quant_ids=[quant.id]))
        quant.invalidate_recordset()
        self.assertFalse(quant.inventory_quantity_set)
        quant.inventory_quantity = 7
        self._rpc('/barcode-adjustment/apply_multiple_inventory', quant_ids=[quant.id])
        quant.invalidate_recordset()
        self.assertEqual(quant.quantity, 7)

    def test_routes_reject_anonymous(self):
        self.logout()
        with self.assertRaises(Exception):
            self.make_jsonrpc_request('/barcode/barcode-scanned', {
                'barcode': 'CTRL-P', 'picking_id': self.picking.id})
