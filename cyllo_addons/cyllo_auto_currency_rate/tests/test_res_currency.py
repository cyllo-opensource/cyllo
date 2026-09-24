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
from unittest.mock import patch, Mock
import requests
from datetime import date


class TestResCurrency(TransactionCase):

    def setUp(self):
        super(TestResCurrency, self).setUp()
        self.env.cr.execute("ALTER TABLE res_company ALTER COLUMN security_lead SET DEFAULT 0.0")
        self.company = self.env['res.company'].create({
            'name': 'Test Currency Company',
            'currency_id': self.env.ref('base.USD').id,
            'enable_currency_update': True,
        })
        self.currency_eur = self.env.ref('base.EUR')
        self.currency_inr = self.env.ref('base.INR') # assuming INR exists or I should create it
        if not self.currency_inr:
             self.currency_inr = self.env['res.currency'].create({
                 'name': 'INR',
                 'symbol': '₹',
                 'active': True
             })
        self.currency_eur.active = True
        self.currency_inr.active = True

    def test_call_erapi_api_success(self):
        """Test successful response from ER-API."""
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {
                'result': 'success',
                'rates': {'EUR': 0.92, 'INR': 83.5}
            }
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response

            rates = self.env['res.currency']._call_erapi_api('USD')
            
            self.assertEqual(rates['EUR'], 0.92)
            self.assertEqual(rates['INR'], 83.5)

    def test_call_erapi_api_failure(self):
        """Test failure response from ER-API."""
        with patch('requests.get') as mock_get:
            mock_get.side_effect = requests.exceptions.RequestException("Connection error")
            
            rates = self.env['res.currency']._call_erapi_api('USD')
            self.assertFalse(rates)

    def test_call_fixer_api_success(self):
        """Test successful response from Fixer API."""
        self.company.fixer_api_key = 'dummy_key'
        
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            # Fixer returns rates in EUR base usually
            mock_response.json.return_value = {
                'success': True,
                'rates': {'USD': 1.1, 'INR': 90.0} # 1 EUR = 1.1 USD, 1 EUR = 90 INR
            }
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response

            # If our base is USD (which is not EUR)
            # Rates should be converted. 
            # USD rate is 1.1. So 1 USD = 1/1.1 = 0.909... EUR
            # Rate for INR in USD base = 90.0 / 1.1 = 81.81...
            
            rates = self.env['res.currency']._call_fixer_api('USD', self.company)
            
            self.assertAlmostEqual(rates['INR'], 90.0/1.1, places=4)

    def test_call_ecb_parser_success(self):
        """Test successful parsing of ECB XML."""
        xml_content = b"""
            <gesmes:Envelope xmlns:gesmes="http://www.gesmes.org/xml/2002-08-01" xmlns="http://www.ecb.int/vocabulary/2002-08-01/eurofxref">
                <Cube>
                    <Cube time="2023-01-01">
                        <Cube currency="USD" rate="1.05"/>
                        <Cube currency="INR" rate="88.5"/>
                    </Cube>
                </Cube>
            </gesmes:Envelope>
        """
        
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.content = xml_content
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            
            # ECB base is EUR.
            # If we ask for USD base:
            # 1 EUR = 1.05 USD.
            # 1 EUR = 88.5 INR.
            # So 1 USD = 88.5 / 1.05 INR
            
            rates = self.env['res.currency']._call_ecb_parser('USD')
            
            self.assertAlmostEqual(rates['INR'], 88.5/1.05, places=4)
            self.assertAlmostEqual(rates['EUR'], 1.0/1.05, places=4)

    def test_call_currency_api_dispatcher(self):
        """Test the dispatcher method call_currency_api."""
        
        # Test ER-API selection
        self.company.currency_update_service = 'erapi'
        with patch.object(type(self.env['res.currency']), '_call_erapi_api') as mock_method:
            mock_method.return_value = {'EUR': 0.9}
            rates = self.env['res.currency']._call_currency_api(self.company, 'USD')
            mock_method.assert_called_once_with('USD')
            self.assertEqual(rates, {'EUR': 0.9})
            
        # Test ECB selection
        self.company.currency_update_service = 'ecb'
        with patch.object(type(self.env['res.currency']), '_call_ecb_parser') as mock_method:
            mock_method.return_value = {'USD': 1.1}
            rates = self.env['res.currency']._call_currency_api(self.company, 'EUR')
            mock_method.assert_called_once_with('EUR')

    def test_update_currency_rates_flow(self):
        """Test the full update flow."""
        self.company.enable_currency_update = True
        
        # Mock API response
        rates_data = {
            self.currency_eur.name: 0.95,
            self.currency_inr.name: 82.0
        }
        
        with patch.object(type(self.env['res.currency']), '_call_currency_api', return_value=rates_data):
            
            self.env['res.currency'].update_currency_rates(self.company.id)
            
            # Check rates created for today
            today = date.today()
            
            # EUR Rate check
            eur_rate = self.env['res.currency.rate'].search([
                ('currency_id', '=', self.currency_eur.id),
                ('name', '=', today),
                ('company_id', '=', self.company.id)
            ])
            self.assertTrue(eur_rate)
            self.assertEqual(eur_rate.company_rate, 0.95)
            
            # INR Rate check
            inr_rate = self.env['res.currency.rate'].search([
                ('currency_id', '=', self.currency_inr.id),
                ('name', '=', today),
                ('company_id', '=', self.company.id)
            ])
            self.assertTrue(inr_rate)
            self.assertEqual(inr_rate.company_rate, 82.0)

    def test_update_currency_rates_disabled(self):
        """Should return False if disabled."""
        self.company.enable_currency_update = False
        
        with patch.object(type(self.env['res.currency']), '_call_currency_api') as mock_api:
            result = self.env['res.currency'].update_currency_rates(self.company.id)
            
            self.assertFalse(result)
            mock_api.assert_not_called()
