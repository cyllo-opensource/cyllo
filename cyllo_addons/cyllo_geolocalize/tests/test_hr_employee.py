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
from unittest.mock import patch
from odoo.tests.common import TransactionCase

class TestHrEmployee(TransactionCase):
    """
    Test cases for geolocalization functionality in the 'hr.employee' model.
    """

    def setUp(self):
        """
        Setup test data for hr.employee geolocalization tests.
        """
        super(TestHrEmployee, self).setUp()
        self.Employee = self.env['hr.employee']
        self.country = self.env['res.country'].search([('code', '=', 'TC')], limit=1)
        if not self.country:
            self.country = self.env['res.country'].create({'name': 'Test Country', 'code': 'TC'})
        
        self.state = self.env['res.country.state'].search([('code', '=', 'TS'), ('country_id', '=', self.country.id)], limit=1)
        if not self.state:
            self.state = self.env['res.country.state'].create({
                'name': 'Test State',
                'code': 'TS',
                'country_id': self.country.id
            })
        self.employee = self.Employee.create({
            'name': 'Test Employee',
            'work_from_home': True,
            'wfh_street': '123 Test St',
            'wfh_city': 'Test City',
            'wfh_zip': '12345',
            'wfh_state_id': self.state.id,
            'wfh_country_id': self.country.id,
        })

    def test_geo_localize_success(self):
        """
        Test successful geolocation for an employee's work-from-home address.
        """
        with patch('odoo.addons.base_geolocalize.models.base_geocoder.GeoCoder.geo_find') as mock_geo_find, \
             patch('odoo.addons.base_geolocalize.models.base_geocoder.GeoCoder.geo_query_address') as mock_geo_query:
            
            mock_geo_query.return_value = 'Test Query'
            mock_geo_find.return_value = (12.345, 67.890)
            
            self.employee.geo_localize()
            
            self.assertAlmostEqual(self.employee.home_latitude, 12.345, places=5)
            self.assertAlmostEqual(self.employee.home_longitude, 67.890, places=5)
            
            self.assertTrue(mock_geo_query.called)
            self.assertTrue(mock_geo_find.called)

    def test_geo_localize_retry(self):
        """
        Test the retry logic in _geo_localize when the first attempt fails to find coordinates.
        """
        with patch('odoo.addons.base_geolocalize.models.base_geocoder.GeoCoder.geo_find') as mock_geo_find, \
             patch('odoo.addons.base_geolocalize.models.base_geocoder.GeoCoder.geo_query_address') as mock_geo_query:
            
            mock_geo_query.side_effect = ['First Query', 'Second Query']
            # First call returns None, second returns coordinates
            mock_geo_find.side_effect = [None, (12.345, 67.890)]
            
            res = self.Employee._geo_localize(street='S', city='C', country='Co')
            
            self.assertEqual(res, (12.345, 67.890))
            self.assertEqual(mock_geo_find.call_count, 2)
