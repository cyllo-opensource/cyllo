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
from unittest.mock import patch, MagicMock
from odoo.tests.common import TransactionCase

class TestResCompany(TransactionCase):
    """
    Test cases for geolocalization functionality in the 'res.company' model.
    """

    def setUp(self):
        """
        Setup test data for res.company geolocalization tests.
        """
        super(TestResCompany, self).setUp()
        self.Company = self.env['res.company']
        self.country = self.env['res.country'].search([('code', '=', 'TCC')], limit=1)
        if not self.country:
            self.country = self.env['res.country'].create({'name': 'Test Country Co', 'code': 'TCC'})
        
        self.state = self.env['res.country.state'].search([('code', '=', 'TSC'), ('country_id', '=', self.country.id)], limit=1)
        if not self.state:
            self.state = self.env['res.country.state'].create({
                'name': 'Test State Co',
                'code': 'TSC',
                'country_id': self.country.id
            })
        self.company = self.Company.create({
            'name': 'Test Company',
            'street': '123 Company St',
            'city': 'Company City',
            'state_id': self.state.id,
            'country_id': self.country.id,
            'zip': '54321',
        })

    def test_geo_localize_browser(self):
        """
        Test browser-based geolocation using mocked geocoder IP lookup.
        """
        with patch('odoo.addons.cyllo_geolocalize.models.res_company.geocoder.ip') as mock_geocoder_ip:
            mock_location = MagicMock()
            mock_location.latlng = [10.0, 20.0]
            mock_geocoder_ip.return_value = mock_location
            
            self.company.geo_localize_browser()
            
            self.assertAlmostEqual(self.company.company_latitude, 10.0, places=5)
            self.assertAlmostEqual(self.company.company_longitude, 20.0, places=5)

    def test_geo_localize(self):
        """
        Test address-based geolocation using mocked external geocoding API.
        """
        with patch('odoo.addons.base_geolocalize.models.base_geocoder.GeoCoder.geo_find') as mock_geo_find, \
             patch('odoo.addons.base_geolocalize.models.base_geocoder.GeoCoder.geo_query_address') as mock_geo_query:
            
            mock_geo_query.return_value = 'Test Query'
            mock_geo_find.return_value = (30.0, 40.0)
            
            self.company.geo_localize()
            
            self.assertAlmostEqual(self.company.company_latitude, 30.0, places=5)
            self.assertAlmostEqual(self.company.company_longitude, 40.0, places=5)
