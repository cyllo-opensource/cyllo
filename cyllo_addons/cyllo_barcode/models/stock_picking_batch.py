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
from odoo import fields, models


class StockPicking(models.Model):
    _inherit = 'stock.picking.batch'

    barcode_recent_scan = fields.Char(string='Recent Scan')
    last_scan_tracking = fields.Char(string='Recent Scan')
    last_scanned_product = fields.Many2one('product.product', string='Recent Scan')

    def batch_barcode_move_line_fields(self):
        """
        Return the list of fields used for barcode-enabled move lines in batch.
        """
        return ["product_id", "quantity_product_uom", "location_id", "location_dest_id", "picking_id",
                "quantity_product_uom", "tracking", "move_id", "result_package_id","lot_id", "is_barcode_scanned"]

    def get_barcode_batch_move_line(self):
        """
        Get barcode-related data for batch move lines, sorted by last update time.
        """
        self.ensure_one()
        response = self.move_line_ids.sorted(key=lambda l: l.write_date).batch_read(self.batch_barcode_move_line_fields())
        return response

    def get_barcode_batch_fields(self):
        """
        Return the list of fields used for barcode-enabled picking batches.
        """
        return ["name", "picking_type_id", "state", "barcode_recent_scan", "last_scan_tracking", "last_scanned_product"]

    def get_barcode_batch(self):
        """
        Get barcode-related data for a picking batch, including its operation type.
        """
        self.ensure_one()
        response = self.read(self.get_barcode_batch_fields())
        response[0]['picking_type'] = self.picking_type_id.code
        return response

    def open_batch_record(self):
        """
        Open the batch record in the client view with predefined parameters.
        """
        return {
            "type": "ir.actions.client",
            "name": self.name,
            "tag": "cyllo_batch_lines_client_action",
            "target": "current",
            'params': {'id': self.id,
                       'name': self.name},
        }

    def open_batch_picking(self):
        """
        Open the related picking batch in form view.
        """
        return {
            'name': self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking.batch',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'current',
        }
