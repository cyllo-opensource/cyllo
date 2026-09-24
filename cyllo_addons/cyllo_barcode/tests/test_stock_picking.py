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

class TestStockPicking(TransactionCase):
    """
    Test cases for 'stock.picking' model, covering UI actions for barcode 
    interfaces and structured data retrieval for scanning.
    """

    def setUp(self):
        """
        Setup test environment for picking operations.
        """
        super(TestStockPicking, self).setUp()
        self.StockPicking = self.env['stock.picking']
        self.PickingType = self.env['stock.picking.type']
        self.Location = self.env['stock.location']

        self.location_src = self.Location.create({'name': 'Source', 'usage': 'internal'})
        self.location_dest = self.Location.create({'name': 'Dest', 'usage': 'internal'})
        
        self.picking_type = self.PickingType.create({
            'name': 'Test Picking Type',
            'code': 'internal',
            'sequence_code': 'TEST',
            'default_location_src_id': self.location_src.id,
            'default_location_dest_id': self.location_dest.id,
        })
        
        self.picking = self.StockPicking.create({
            'picking_type_id': self.picking_type.id,
            'location_id': self.location_src.id,
            'location_dest_id': self.location_dest.id,
        })

    def test_open_record(self):
        """
        Test the action that opens the custom barcode scanning interface.
        """
        action = self.picking.open_record()
        self.assertEqual(action.get('type'), 'ir.actions.client')
        self.assertEqual(action.get('tag'), 'cyllo_location_client_action')
        self.assertEqual(action['params']['id'], self.picking.id)

    def test_open_picking(self):
        """
        Test the action that redirects to the standard picking form view.
        """
        action = self.picking.open_picking()
        self.assertEqual(action.get('type'), 'ir.actions.act_window')
        self.assertEqual(action.get('res_model'), 'stock.picking')
        self.assertEqual(action.get('res_id'), self.picking.id)

    def test_picking_barcode_fields(self):
        """
        Test that the model returns the correct subset of fields required for barcode UI.
        """
        fields = self.picking.picking_barcode_fields()
        expected = ["name", "location_id", "location_dest_id", "state", "barcode_recent_scan", 
                   "last_scan_tracking", "last_scanned_product", "with_barcode", "picking_type_id"]
        for field in expected:
            self.assertIn(field, fields)

    def test_get_barcode_picking(self):
        """
        Test the retrieval of structured JSON data for a picking record.
        """
        data = self.picking.get_barcode_picking()
        self.assertTrue(data)
        self.assertIsInstance(data, list)
        self.assertEqual(data[0]['id'], self.picking.id)
        self.assertEqual(data[0]['picking_type'], 'internal')
