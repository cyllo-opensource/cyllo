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

from odoo.tests import TransactionCase, tagged


@tagged('-at_install', 'post_install')
class TestResPartner(TransactionCase):
    """
    Test suite for validating partner geolocation functionality.

    This suite ensures two behaviors:

        1. The overridden write() triggers geo localization only when required.
        2. The get_location() method correctly handles different API responses.
    """

    def setUp(self):
        """
        Create a test partner record for running all geolocation-related tests.
        """
        super().setUp()
        self.partner = self.env['res.partner'].create({
            'name': 'Test Partner',
            'street': 'Old Street',
            'zip': '12345',
        })


    def test_write(self):
        """
        Validate write() behavior:

            ✔ Updating unrelated fields → geo_localize() MUST NOT run.
            ✔ Updating street → MUST trigger.
            ✔ Updating zip → MUST trigger.
            ✔ Updating both → MUST trigger only once.
        """

        with patch.object(self.partner.__class__, 'geo_localize') as mock_geo:
            self.partner.write({'phone': '9876543210'})
            mock_geo.assert_not_called()
        with patch.object(self.partner.__class__, 'geo_localize') as mock_geo:
            self.partner.write({'street': 'New Road'})
            mock_geo.assert_called_once()
        with patch.object(self.partner.__class__, 'geo_localize') as mock_geo:
            self.partner.write({'zip': '560001'})
            mock_geo.assert_called_once()
        with patch.object(self.partner.__class__, 'geo_localize') as mock_geo:
            self.partner.write({'street': 'MG Road', 'zip': '67890'})
            mock_geo.assert_called_once()

    def test_get_location_responses(self):
        """
        Validate get_location() behavior with mocked API responses:

            ✔ Valid API response → returns first result.
            ✔ Empty response → returns None.
            ✔ API failure → returns False.
        """

        mock_valid = MagicMock()
        mock_valid.json.return_value = [{'lat': '10.123', 'lon': '20.456'}]
        with patch('requests.get', return_value=mock_valid), \
             patch('time.sleep', return_value=None):
            result = self.partner.get_location("Street 1", "12345", "India")
            self.assertEqual(
                result,
                {'lat': '10.123', 'lon': '20.456'},
            )
        mock_empty = MagicMock()
        mock_empty.json.return_value = []
        with patch('requests.get', return_value=mock_empty), \
             patch('time.sleep', return_value=None):
            result = self.partner.get_location("Unknown", "00000", "Atlantis")
            self.assertIsNone(result)
        with patch('requests.get', side_effect=Exception("API Failure")), \
             patch('time.sleep', return_value=None):
            result = self.partner.get_location("X", "99999", "Mars")
            self.assertFalse(result)
