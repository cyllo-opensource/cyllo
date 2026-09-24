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
from odoo import models


class BarcodeDataReport(models.AbstractModel):
    """ Barcode Data Report"""
    _name = "report.cyllo_barcode.barcode_data_report"
    _description = "Cyllo Barcode Pdf Report"

    def _get_report_values(self, docids, data):
        """Return report datas"""
        model = data.get('mode')
        data = {
            'mode': model,
        }
        if model == 'product.product':
            data['items'] = self.env[model].search_read([], ['name', 'barcode'])
        elif model == 'stock.picking.type':
            data['items'] = self.env[model].search_read([], ['name', 'barcode'])
        elif model == 'stock.location':
            data['items'] = self.env['stock.location'].search_read([("usage", "=", "internal")], ['name', 'barcode'])
        return data
