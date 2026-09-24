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
    _inherit = 'stock.picking'

    with_barcode = fields.Boolean(string='With Barcode')
    barcode_recent_scan = fields.Char(string='Recent Scan')
    last_scan_tracking = fields.Char(string='Recent Scan')
    last_scanned_product = fields.Many2one('product.product', string='Recent Scan')

    def open_record(self):
        """
        Open the record in the client view with predefined context and parameters.
        """
        return {
            "type": "ir.actions.client",
            "name": self.name,
            "tag": "cyllo_location_client_action",
            "target": "current",
            "context": {
                'menu': 'cyllo_stock_picking_client_action',
            },
            'params': {'id': self.id,
                       'name': self.name},
        }

    def open_picking(self):
        """
        Open the related stock picking in form view.
        """
        return {
            'name': self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'current',
        }

    def picking_barcode_fields(self):
        """
        Return the list of fields used for barcode-enabled pickings.
        """
        return ["name", "location_id", "location_dest_id", "state", "barcode_recent_scan", "last_scan_tracking",
                "last_scanned_product", "with_barcode", "picking_type_id"]

    def get_barcode_picking(self):
        """
        Get barcode-related data for the picking, including its operation type.
        """
        self.ensure_one()
        response = self.read(self.picking_barcode_fields())
        for res in response:
            res['picking_type'] = self.picking_type_id.code
        return response
