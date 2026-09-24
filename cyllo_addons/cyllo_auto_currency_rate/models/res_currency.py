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
import logging
import requests
from lxml import etree

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class ResCurrency(models.Model):
    """inherit res.currency model to add methods for fetching auto currency rates"""
    _inherit = 'res.currency'

    @api.model
    def _call_currency_api(self, company_id, base_currency='USD'):
        """
        Single function to call any currency service API based on user selection in config
        and handle the result.
        Returns: dict with currency rates or False on failure

        Example return format:
        {
            'USD': 1.0850,
            'GBP': 0.8650,
            'INR': 89.50,
            ...
        }
        """
        # Check the service selected
        update_service = company_id.currency_update_service
        rates = {}

        # ExchangeRate-API
        if update_service == 'erapi':
            rates = self._call_erapi_api(base_currency)
        # European Central Bank parser
        if update_service == 'ecb':
            rates = self._call_ecb_parser(base_currency)
        # Fixer-API
        if update_service == 'fixer':
            rates = self._call_fixer_api(base_currency, company_id)

        return rates

    def _call_fixer_api(self, base_currency, company_id):
        """Function to call fixer api.
         return dict with currency rates or False on failure"""

        try:
            access_key = company_id.fixer_api_key
            url = f"https://data.fixer.io/api/latest?access_key={access_key}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            if not data.get('success') or not data.get('rates'):
                _logger.error(_('Error in fixer'))
                return False

            rates = data.get('rates')  # Fixer-API result in Euro
            # converting if company currency is not Euro
            if base_currency != 'EUR':
                base_rate = data['rates'].get(base_currency)
                if base_rate == 1:
                    _logger.error(
                        _(f"Fixer API does not contain {base_currency} currency"))
                    return False
                for currency, rate in rates.items():
                    rates[currency] = round(rate / base_rate, 6)
            return rates

        except requests.exceptions.Timeout:
            _logger.error(_("Currency API request timed out"))
            return False
        except requests.exceptions.RequestException as e:
            _logger.error(_(f"Error calling currency API: {str(e)}"))
            return False
        except Exception as e:
            _logger.error(_(f"Unexpected error in currency API call: {str(e)}"))
            return False

    def _call_erapi_api(self, base_currency):
        """Function to call erapi api.
         return dict with currency rates or False on failure"""

        try:
            url = f"https://api.exchangerate-api.com/v4/latest/{base_currency}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            # ExchangeRate-API response in base currency
            if data.get('rates'):
                return data.get('rates')
            return False

        except requests.exceptions.Timeout:
            _logger.error(_("Currency API request timed out"))
            return False
        except requests.exceptions.RequestException as e:
            _logger.error(_(f"Error calling currency API: {str(e)}"))
            return False
        except Exception as e:
            _logger.error(_(f"Unexpected error in currency API call: {str(e)}"))
            return False

    def _call_ecb_parser(self, base_currency):
        """Function to call ecb parser.
         return dict with currency rates or False on failure"""

        try:
            url = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            root = etree.fromstring(
                response.content)  # Result in ECB base currency(EUR) as xml

            namespace = {
                "ecb": "http://www.ecb.int/vocabulary/2002-08-01/eurofxref"}  # all Cube tags belong to this namespace.

            rates = {"EUR": 1.0}  # ECB base currency
            base_rate = 1.0

            # converting base rate if company currency is not Euro
            if base_currency != 'EUR':
                node = root.find(f".//ecb:Cube[@currency='{base_currency}']",
                                 namespace)  # use prefix ecb to find correct tag
                if node is None:
                    _logger.error(
                        _("Ecb response does not contain base currency"))
                    return False
                base_rate = float(node.attrib["rate"])
                rates["EUR"] = 1.0 / base_rate

            for cube in root.findall(".//ecb:Cube[@currency]", namespace):
                rates[cube.attrib["currency"]] = round(
                    float(cube.attrib["rate"]) / base_rate, 6)

            return rates if len(rates) >= 2 else False

        except requests.exceptions.Timeout:
            _logger.error(_("Ecb parser request timed out"))
            return False
        except requests.exceptions.RequestException as e:
            _logger.error(_(f"Error calling Ecb parser: {str(e)}"))
            return False
        except Exception as e:
            _logger.error(_(f"Unexpected error in Ecb parser: {str(e)}"))
            return False

    @api.model
    def update_currency_rates(self, company_id):
        """
        Scheduled action method to update all active currency rates
        Uses single API call for efficiency
        """
        # Check if auto-update is enabled
        company_id = self.env['res.company'].browse(company_id)
        auto_update = company_id.enable_currency_update

        if not auto_update or auto_update == 'False':
            _logger.info(
                _("Currency auto-update is disabled. Skipping scheduled update."))
            return False

        # Get all active currencies
        currencies = self.search([
            ('active', '=', True),
        ])
        _logger.info(
            _(f"Starting scheduled currency rate update for {len(currencies)} currencies"))

        # Call API once to get all rates
        base_currency = company_id.currency_id.name
        rates_data = self._call_currency_api(company_id, base_currency)

        if not rates_data:
            _logger.error(_("Failed to fetch currency rates from API"))
            return False

        # Update all currencies using the fetched data
        success_count = 0
        rate_obj = self.env['res.currency.rate']
        today = fields.Date.today()

        for currency in currencies:
            try:
                if currency.name not in rates_data:
                    _logger.warning(
                        _(f"Currency {currency.name} not found in API response"))
                    continue

                new_rate = rates_data[currency.name]

                # Create or update rate
                existing_rate = rate_obj.search([
                    ('currency_id', '=', currency.id),
                    ('name', '=', today),
                    ('company_id', '=', company_id.id)
                ], limit=1)

                if not existing_rate:
                    rate_obj.create({
                        'currency_id': currency.id,
                        'name': today,
                        'company_rate': new_rate,
                        'company_id': company_id.id
                    })
                else:
                    existing_rate.company_rate = new_rate

                success_count += 1

            except Exception as e:
                _logger.error(_(f"Failed to update {currency.name}: {str(e)}"))
                continue

        _logger.info(_(
            f"Scheduled currency rate update completed. {success_count}/{len(currencies)} currencies updated."))

        return True
