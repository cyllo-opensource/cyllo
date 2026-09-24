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

class TestStockMove(TransactionCase):
    """
    Test cases for 'stock.move' extensions, focusing on done quantity 
    computations during barcode processing.
    """

    def setUp(self):
        """
        Setup test environment for stock move operations.
        """
        super(TestStockMove, self).setUp()
        self.StockMove = self.env['stock.move']
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

    def test_compute_done_quantity(self):
        """
        Test that 'done_quantity' reflects accurately when barcode mode is enabled.
        """
        self.move.quantity = 5
        self.move.with_barcode = True
        self.move._compute_done_quantity()
        self.assertEqual(self.move.done_quantity, 5)

        self.move.with_barcode = False
        self.move._compute_done_quantity()
        self.assertEqual(self.move.done_quantity, 0)

    def test_inverse_done_quantity(self):
        """
        Test that manually setting 'done_quantity' correctly updates the move's actual quantity.
        """
        self.move.done_quantity = 8
        self.move._inverse_done_quantity()
        self.assertEqual(self.move.quantity, 8)
