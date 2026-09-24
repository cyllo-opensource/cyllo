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
import geocoder
from odoo import api, fields, models


class ResCompany(models.Model):
    """
    Inherited the res.company model to add geographic localization capabilities,
    including fields for coordinates (latitude, longitude) and methods
    to detect and update the company's location.
    """
    _inherit = 'res.company'

    company_latitude = fields.Float('Geo Latitude', digits=(10, 7))
    company_longitude = fields.Float('Geo Longitude', digits=(10, 7))
    range = fields.Integer('Range')

    def geo_localize_browser(self):
        """
        Detects the company's geographic location using the browser's IP address.
        """
        for company in self:
            location = geocoder.ip('me')
            latitude = location.latlng[0] if location.latlng else None
            longitude = location.latlng[1] if location.latlng else None
            if latitude and longitude:
                company.write({
                    'company_latitude': latitude,
                    'company_longitude': longitude,
                })

    @api.model
    def _geo_localize(self, street='', zip='', city='', state='', country=''):
        """
        Retrieves geographic coordinates (latitude and longitude)
        for a given company address.

        Args:
            street (str): The street address.
            zip (str): The postal code.
            city (str): The city.
            state (str): The state name.
            country (str): The country name.

        Returns:
            tuple: A tuple containing latitude and longitude (float) if found,
                   otherwise None.
        """
        geo_obj = self.env['base.geocoder']
        search = geo_obj.geo_query_address(street=street, zip=zip, city=city,
                                           state=state, country=country)
        result = geo_obj.geo_find(search, force_country=country)
        if result is None:
            search = geo_obj.geo_query_address(city=city, state=state,
                                               country=country)
            result = geo_obj.geo_find(search, force_country=country)
        return result

    def geo_localize(self):
        """
        Updates the company's geographic coordinates (latitude and longitude)
        based on its address using the `_geo_localize` method.

        Returns:
            bool: True if the operation is successful.
        """
        for company in self:
            result = self._geo_localize(company.street,
                                        company.zip,
                                        company.city,
                                        company.state_id.name,
                                        company.country_id.name)
            if result:
                company.write({
                    'company_latitude': result[0],
                    'company_longitude': result[1],
                })
        return True
