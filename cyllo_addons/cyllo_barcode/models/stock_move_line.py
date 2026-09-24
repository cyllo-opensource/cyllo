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


class StockMoveLine(models.Model):
    """
    StockMoveLine class is used to assigning serial number to the received products
    """
    _inherit = 'stock.move.line'

    lot_serial_name = fields.Char(string='Scanned Lot Serial')
    is_barcode_scanned = fields.Boolean(string='Barcode Scanned')
    had_location_by_barcode = fields.Boolean(help='Location Assigned By Barcode')
    had_location_by_barcode_dest = fields.Boolean(help='Location Assigned By Barcode for Destination')

    def batch_read(self, fields_list):
        """
        Read the given fields for records and include move quantities in the response.
        """
        response = self.read(fields_list)
        for rec in self:
            matching_obj = next((obj for obj in response if obj.get('id') == rec.id), None)
            if matching_obj:
                matching_obj['move_id'] = rec.move_id.read(["product_uom_qty"])
        return response
