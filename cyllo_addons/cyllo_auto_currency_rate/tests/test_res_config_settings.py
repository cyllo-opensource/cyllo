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
from unittest.mock import patch


class TestResConfigSettings(TransactionCase):

    def setUp(self):
        super(TestResConfigSettings, self).setUp()
        self.env.cr.execute("ALTER TABLE res_company ALTER COLUMN security_lead SET DEFAULT 0.0")
        self.company = self.env['res.company'].create({
            'name': 'Test Config Company',
            'currency_id': self.env.ref('base.USD').id,
        })
        self.user = self.env['res.users'].create({
            'name': 'Test User',
            'login': 'testuser',
            'company_id': self.company.id,
            'company_ids': [(6, 0, [self.company.id])],
            'groups_id': [(6, 0, [self.env.ref('base.group_system').id])]
        })

    def test_settings_save(self):
        """Test that settings save to company and update cron."""
        # Switch to the test user/company context
        self.env = self.env(user=self.user)
        
        config = self.env['res.config.settings'].create({
            'enable_currency_update': True,
            'currency_update_interval': 'weeks',
            'currency_update_service': 'ecb',
        })
        config.set_values()

        # Check company fields
        self.assertTrue(self.company.enable_currency_update)
        self.assertEqual(self.company.currency_update_interval, 'weeks')
        self.assertEqual(self.company.currency_update_service, 'ecb')

        # Check cron created
        cron = self.company.currency_cron_id
        self.assertTrue(cron)
        self.assertTrue(cron.active)
        self.assertEqual(cron.interval_type, 'weeks')

    def test_manual_update_action(self):
        """Test action_update_currency_rates_now."""
        self.env = self.env(user=self.user)
        
        config = self.env['res.config.settings'].create({})
        
        # We need at least one other active currency to avoid UserError
        eur = self.env.ref('base.EUR')
        eur.active = True
        
        with patch('odoo.addons.cyllo_auto_currency_rate.models.res_currency.ResCurrency.update_currency_rates') as mock_update:
            mock_update.return_value = True
            
            result = config.action_update_currency_rates_now()
            
            mock_update.assert_called_once_with(self.company.id)
            self.assertEqual(result['params']['type'], 'success')

    def test_manual_update_action_failure(self):
        """Test action_update_currency_rates_now failure case."""
        self.env = self.env(user=self.user)
        config = self.env['res.config.settings'].create({})
        
        # Ensure active currency exists
        eur = self.env.ref('base.EUR')
        eur.active = True

        with patch('odoo.addons.cyllo_auto_currency_rate.models.res_currency.ResCurrency.update_currency_rates') as mock_update:
            mock_update.return_value = False
            
            result = config.action_update_currency_rates_now()
            
            mock_update.assert_called_once_with(self.company.id)
            self.assertEqual(result['params']['type'], 'warning')

    def test_manual_update_no_currencies(self):
        """Test that UserError is raised if no other currencies are active."""
        self.env = self.env(user=self.user)
        config = self.env['res.config.settings'].create({})
        
        # Deactivate all other currencies
        currencies = self.env['res.currency'].search([
            ('id', '!=', self.company.currency_id.id)
        ])
        currencies.write({'active': False})

        with self.assertRaises(Exception) as cm: # UserError
             config.action_update_currency_rates_now()
        
