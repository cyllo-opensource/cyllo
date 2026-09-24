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


class TestResCompany(TransactionCase):

    def setUp(self):
        super(TestResCompany, self).setUp()
        self.env.cr.execute("ALTER TABLE res_company ALTER COLUMN security_lead SET DEFAULT 0.0")
        self.company = self.env['res.company'].create({
            'name': 'Test Company',
            'currency_id': self.env.ref('base.USD').id,
        })

    def test_default_values(self):
        """Test default values on creation."""
        self.assertFalse(self.company.enable_currency_update)
        self.assertEqual(self.company.currency_update_service, 'erapi')
        # Since no cron is created yet, compute should set it to manual
        self.assertEqual(self.company.currency_update_interval, 'manual')

    def test_update_currency_cron_creation(self):
        """Test that _update_currency_cron creates a cron job."""
        self.company.enable_currency_update = True
        self.company.currency_update_interval = 'days'
        self.company.currency_update_service = 'erapi'
        
        # Manually call _update_currency_cron since it's not triggered by write on company
        self.company._update_currency_cron()

        cron = self.company.currency_cron_id
        self.assertTrue(cron, "Cron should be created")
        self.assertEqual(cron.name, f'Currency Rate Update - {self.company.name}')
        self.assertEqual(cron.interval_type, 'days')
        self.assertEqual(cron.interval_number, 1)
        self.assertTrue(cron.active)
        self.assertEqual(cron.model_id.model, 'res.currency')
        self.assertIn(f'model.update_currency_rates({self.company.id})', cron.code)

    def test_update_currency_cron_update(self):
        """Test that _update_currency_cron updates existing cron."""
        self.company.enable_currency_update = True
        self.company.currency_update_interval = 'days'
        self.company._update_currency_cron()
        
        cron = self.company.currency_cron_id
        self.assertEqual(cron.interval_type, 'days')

        # Change interval and update
        self.company.currency_update_interval = 'weeks'
        self.company._update_currency_cron()

        self.assertEqual(cron.interval_type, 'weeks', "Cron interval should be updated")

    def test_disable_currency_update(self):
        """Test that disabling update deactivates the cron."""
        self.company.enable_currency_update = True
        self.company.currency_update_interval = 'days'
        self.company._update_currency_cron()
        
        cron = self.company.currency_cron_id
        self.assertTrue(cron.active)

        # Disable
        self.company.enable_currency_update = False
        self.company._update_currency_cron()
        
        self.assertFalse(cron.active, "Cron should be deactivated")

    def test_manual_interval_disables_cron(self):
        """Test that setting interval to manual deactivates the cron."""
        self.company.enable_currency_update = True
        self.company.currency_update_interval = 'days'
        self.company._update_currency_cron()
        
        cron = self.company.currency_cron_id
        self.assertTrue(cron.active)

        # Set to manual
        self.company.currency_update_interval = 'manual'
        self.company._update_currency_cron()
        
        self.assertFalse(cron.active, "Cron should be deactivated when manual")

    def test_compute_interval(self):
        """Test _compute_currency_update_interval logic."""
        # Initial state
        self.assertEqual(self.company.currency_update_interval, 'manual')
        
        # Create cron
        self.company.enable_currency_update = True
        self.company.currency_update_interval = 'days'
        self.company._update_currency_cron()
        
        # Trigger compute
        self.company._compute_currency_update_interval()
        self.assertEqual(self.company.currency_update_interval, 'days')
