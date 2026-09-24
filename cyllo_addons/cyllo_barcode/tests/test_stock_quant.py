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

class TestStockQuant(TransactionCase):
    """
    Test cases for 'stock.quant' model, focusing on tracking records 
    created specifically through the barcode interface.
    """

    def setUp(self):
        """
        Setup test environment for inventory quant operations.
        """
        super(TestStockQuant, self).setUp()
        self.StockQuant = self.env['stock.quant']
        self.Product = self.env['product.product']
        self.Location = self.env['stock.location']
        
        self.product = self.Product.create({'name': 'Test Product', 'type': 'product'})
        self.location = self.Location.create({'name': 'Stock'})

    def test_created_cyllo_barcode(self):
        """
        Test the verification flag for quants initialized via barcode scanning.
        """
        quant = self.StockQuant.create({
            'product_id': self.product.id,
            'location_id': self.location.id,
            'quantity': 10,
            'created_cyllo_barcode': True
        })
        self.assertTrue(quant.created_cyllo_barcode)
