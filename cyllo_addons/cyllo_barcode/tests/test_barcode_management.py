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
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError

class TestBarcodeManagement(TransactionCase):
    """
    Test cases for 'barcode.management' model, covering core barcode scanning
    logic for products, locations, and tracked items (Lots/Serials).
    """

    def setUp(self):
        """
        Setup test environment for barcode management, including products,
        locations, and picking types.
        """
        super(TestBarcodeManagement, self).setUp()
        self.BarcodeManagement = self.env['barcode.management']
        self.StockPicking = self.env['stock.picking']
        self.Product = self.env['product.product']
        self.Location = self.env['stock.location']
        self.PickingType = self.env['stock.picking.type']
        
        self.location_1 = self.Location.create({
            'name': 'Test Location 1',
            'usage': 'internal',
            'barcode': 'LOC1'
        })
        self.location_2 = self.Location.create({
            'name': 'Test Location 2',
            'usage': 'internal',
            'barcode': 'LOC2'
        })
        
        self.picking_type_in = self.env.ref('stock.picking_type_in', raise_if_not_found=False)
        if not self.picking_type_in:
             self.picking_type_in = self.PickingType.create({
                'name': 'Receipts',
                'code': 'incoming',
                'sequence_code': 'IN',
                'default_location_dest_id': self.location_1.id,
            })

        self.product_no_tracking = self.Product.create({
            'name': 'Product No Tracking',
            'type': 'product',
            'barcode': '1234567890',
            'tracking': 'none',
        })
        self.product_serial = self.Product.create({
            'name': 'Product Serial',
            'type': 'product',
            'barcode': 'SERIAL123',
            'tracking': 'serial',
        })
        self.product_lot = self.Product.create({
            'name': 'Product Lot',
            'type': 'product',
            'barcode': 'LOT123',
            'tracking': 'lot',
        })

        self.picking = self.StockPicking.create({
            'picking_type_id': self.picking_type_in.id,
            'location_id': self.env.ref('stock.stock_location_suppliers').id,
            'location_dest_id': self.location_1.id,
        })

    def test_return_barcode_models(self):
        """
        Test the retrieval of models supported for barcode scanning.
        """
        res = self.BarcodeManagement.return_barcode_models()
        self.assertIn('product.product', res)
        self.assertIn('stock.picking', res)
        self.assertEqual(res['product.product'], 'barcode')

    def test_search_barcode_in_models_product(self):
        """
        Test searching for a specific product by its barcode.
        """
        res = self.BarcodeManagement.search_barcode_in_models('1234567890', self.picking.id)
        self.assertFalse(res['is_error'])
        self.assertEqual(res['res_model'], 'product.product')
        self.assertEqual(res['data'][0]['id'], self.product_no_tracking.id)

    def test_search_barcode_in_models_invalid(self):
        """
        Test the error handling when an unrecognized barcode is scanned.
        """
        res = self.BarcodeManagement.search_barcode_in_models('INVALID', self.picking.id)
        self.assertTrue(res['is_error'])

    def test_add_stock_move_line_no_tracking(self):
        """
        Test adding a stock move line for a non-tracked product via barcode.
        """
        self.BarcodeManagement.add_stock_move_line(
            picking_id=self.picking.id,
            res_model='product.product',
            data=[{'id': self.product_no_tracking.id}],
            barcode='1234567890'
        )
        move = self.picking.move_ids_without_package.filtered(lambda m: m.product_id == self.product_no_tracking)
        self.assertTrue(move)
        self.assertEqual(move.quantity, 1)

    def test_add_stock_location_incoming(self):
        """
        Test updating the destination location by scanning its barcode during receipt.
        """
        self.BarcodeManagement.add_stock_move_line(
            picking_id=self.picking.id,
            res_model='product.product',
            data=[{'id': self.product_no_tracking.id}],
            barcode='1234567890'
        )
        
        self.BarcodeManagement.add_stock_location(
            picking_id=self.picking.id,
            picking_type='incoming',
            data=[{'id': self.location_2.id}],
            res_model='stock.location'
        )
        
        self.assertEqual(self.picking.location_dest_id.id, self.location_2.id)
        for line in self.picking.move_line_ids:
            self.assertEqual(line.location_dest_id.id, self.location_2.id)
            self.assertTrue(line.had_location_by_barcode)

    def test_assign_recent_scan(self):
        """
        Test the recording of the most recently scanned item for UI feedback.
        """
        self.BarcodeManagement.assign_recent_scan(
            res_id=self.picking.id,
            model_name='product.product',
            tracking='none',
            product=self.product_no_tracking.id,
            res_model='stock.picking'
        )
        self.assertEqual(self.picking.barcode_recent_scan, 'product.product')
        self.assertEqual(self.picking.last_scanned_product.id, self.product_no_tracking.id)

    def test_handle_barcode_scan_serial(self):
        """
        Test processing a serial number barcode scan for a tracked product.
        """
        self.BarcodeManagement._handle_barcode_scan(self.picking, "SN001", self.product_serial)
        
        move_line = self.picking.move_line_ids.filtered(lambda l: l.product_id == self.product_serial)
        self.assertTrue(move_line)
        self.assertEqual(move_line.lot_name, "SN001")
        self.assertEqual(move_line.quantity, 1)

    def test_handle_barcode_scan_duplicate_serial(self):
        """
        Test that scanning the same serial number twice triggers a validation error.
        """
        self.BarcodeManagement._handle_barcode_scan(self.picking, "SN001", self.product_serial)
        with self.assertRaises(UserError):
             self.BarcodeManagement._handle_barcode_scan(self.picking, "SN001", self.product_serial)
