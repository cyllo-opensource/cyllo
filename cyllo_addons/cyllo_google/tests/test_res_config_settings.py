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
from odoo.tests import common


class TestCylloGoogleSettings(common.TransactionCase):
    """Tests for the Google credential settings."""

    PARAMS = {
        'access_token': 'cyllo_google.access_token',
        'client_id': 'cyllo_google.client_id',
        'client_secret': 'cyllo_google.client_secret',
        'refresh_token': 'cyllo_google.refresh_token',
    }

    def _settings(self, **values):
        return self.env['res.config.settings'].create(values)

    def test_fields_are_declared(self):
        """All four Google credential fields exist on the settings model."""
        fields = self.env['res.config.settings']._fields
        for field_name in self.PARAMS:
            self.assertIn(field_name, fields)

    def test_set_values_stores_parameters(self):
        """Saving the settings persists every credential as a system parameter."""
        self._settings(
            access_token='token-abc',
            client_id='client-123',
            client_secret='secret-xyz',
            refresh_token='refresh-789',
        ).execute()
        params = self.env['ir.config_parameter'].sudo()
        self.assertEqual(params.get_param(self.PARAMS['access_token']), 'token-abc')
        self.assertEqual(params.get_param(self.PARAMS['client_id']), 'client-123')
        self.assertEqual(params.get_param(self.PARAMS['client_secret']), 'secret-xyz')
        self.assertEqual(params.get_param(self.PARAMS['refresh_token']), 'refresh-789')

    def test_get_values_reads_parameters(self):
        """A newly opened settings record is pre-filled from the parameters."""
        params = self.env['ir.config_parameter'].sudo()
        params.set_param(self.PARAMS['access_token'], 'stored-token')
        params.set_param(self.PARAMS['client_id'], 'stored-client')
        params.set_param(self.PARAMS['client_secret'], 'stored-secret')
        params.set_param(self.PARAMS['refresh_token'], 'stored-refresh')

        settings = self._settings()
        self.assertEqual(settings.access_token, 'stored-token')
        self.assertEqual(settings.client_id, 'stored-client')
        self.assertEqual(settings.client_secret, 'stored-secret')
        self.assertEqual(settings.refresh_token, 'stored-refresh')

    def test_empty_values_are_stored_as_blank(self):
        """Clearing a credential blanks the parameter instead of leaving it stale."""
        params = self.env['ir.config_parameter'].sudo()
        self._settings(access_token='to-be-cleared').execute()
        self.assertEqual(params.get_param(self.PARAMS['access_token']), 'to-be-cleared')
        self._settings(access_token=False).execute()
        self.assertFalse(params.get_param(self.PARAMS['access_token']))
