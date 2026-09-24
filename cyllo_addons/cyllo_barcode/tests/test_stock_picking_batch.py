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

class TestStockPickingBatch(TransactionCase):
    """
    Test cases for 'stock.picking.batch', covering batch processing UI 
    actions and barcode integration for grouped transfers.
    """

    def setUp(self):
        """
        Setup test environment for batch picking operations.
        """
        super(TestStockPickingBatch, self).setUp()
        self.Batch = self.env['stock.picking.batch']
        self.PickingType = self.env['stock.picking.type']
        self.Picking = self.env['stock.picking']

        self.picking_type = self.PickingType.create({
            'name': 'Batch Type',
            'code': 'internal',
            'sequence_code': 'BATCH',
        })

        self.batch = self.Batch.create({
            'picking_type_id': self.picking_type.id,
        })

    def test_open_batch_record(self):
        """
        Test the action that opens the custom batch barcode scanning interface.
        """
        action = self.batch.open_batch_record()
        self.assertEqual(action['type'], 'ir.actions.client')
        self.assertEqual(action['tag'], 'cyllo_batch_lines_client_action')
        self.assertEqual(action['params']['id'], self.batch.id)

    def test_open_batch_picking(self):
        """
        Test the action that redirects to the standard batch form view.
        """
        action = self.batch.open_batch_picking()
        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(action['res_model'], 'stock.picking.batch')
        self.assertEqual(action['res_id'], self.batch.id)

    def test_get_barcode_batch(self):
        """
        Test the retrieval of structured JSON data for a batch record.
        """
        data = self.batch.get_barcode_batch()
        self.assertTrue(data)
        self.assertIsInstance(data, list)
        self.assertEqual(data[0]['id'], self.batch.id)
        self.assertEqual(data[0]['picking_type'], 'internal')

    def test_batch_barcode_move_line_fields(self):
        """
        Test that the batch model returns the correct move line fields for UI display.
        """
        fields = self.batch.batch_barcode_move_line_fields()
        self.assertIn('product_id', fields)
