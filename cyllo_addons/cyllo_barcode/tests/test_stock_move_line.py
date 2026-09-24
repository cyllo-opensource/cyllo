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

class TestStockMoveLine(TransactionCase):
    """
    Test cases for 'stock.move.line' extensions, covering integration 
    with barcode scanning and batch data retrieval.
    """

    def setUp(self):
        """
        Setup test environment for stock move line operations.
        """
        super(TestStockMoveLine, self).setUp()
        self.StockMove = self.env['stock.move']
        self.StockMoveLine = self.env['stock.move.line']
        self.Product = self.env['product.product']
        self.Location = self.env['stock.location']
        
        self.product = self.Product.create({'name': 'Test Product', 'type': 'product'})
        self.location_src = self.Location.create({'name': 'Source'})
        self.location_dest = self.Location.create({'name': 'Dest'})

        self.move = self.StockMove.create({
            'name': 'Test Move',
            'product_id': self.product.id,
            'product_uom_qty': 10,
            'location_id': self.location_src.id,
            'location_dest_id': self.location_dest.id,
        })
        
        self.move_line = self.StockMoveLine.create({
            'move_id': self.move.id,
            'product_id': self.product.id,
            'quantity': 5,
            'location_id': self.location_src.id,
            'location_dest_id': self.location_dest.id,
        })

    def test_fields_exist(self):
        """
        Confirm that extended fields for barcode tracking exist on the model.
        """
        self.assertTrue(hasattr(self.move_line, 'lot_serial_name'))
        self.assertTrue(hasattr(self.move_line, 'is_barcode_scanned'))
        self.assertTrue(hasattr(self.move_line, 'had_location_by_barcode'))

    def test_batch_read(self):
        """
        Test the custom RPC method for optimized data retrieval in barcode interfaces.
        """
        res = self.move_line.batch_read(['product_id', 'quantity'])
        self.assertTrue(res)
        self.assertEqual(res[0]['id'], self.move_line.id)
        self.assertIn('move_id', res[0])
        self.assertEqual(res[0]['move_id'][0]['id'], self.move.id)
