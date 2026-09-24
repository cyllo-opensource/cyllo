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
import requests
import time

from odoo import models


class ResPartner(models.Model):
    """
    Inherits the base 'res.partner' model and  add function to it.
    """
    _inherit = 'res.partner'

    def write(self, vals):
        """Override the write method to trigger geo localization when 'street' or 'zip' fields are updated."""
        res = super(ResPartner, self).write(vals)
        if 'street' in vals.keys() or 'zip' in vals.keys():
            self.geo_localize()
        return res

    def get_location(self, street, pincode, country_name):
        """Get location data using Nominatim API based on provided address parameters."""
        try:
            response = requests.get('https://nominatim.openstreetmap.org/search', params={
                'limit': 1,
                'format': 'json',
                'street': street or '',
                'postalcode': pincode or '',
                'city': '',
                'state': '',
                'country': country_name or '',
            })
            data = response.json()
            time.sleep(1)
            return data[0] if data else None
        except Exception:
            return False
