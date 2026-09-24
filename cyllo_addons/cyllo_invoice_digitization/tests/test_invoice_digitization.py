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
from odoo.tests.common import TransactionCase, tagged


@tagged('-at_install', 'post_install')
class TestInvoiceDigitization(TransactionCase):
    """
    Test suite for validating configuration behavior of the `invoice.digitization` model.

    Ensures that:
        - Only one active configuration exists per account type.
        - Activation logic correctly updates previous active records.
        - Vendor and customer configurations work independently.
    """

    @classmethod
    def setUpClass(cls):
        """
        Prepare a clean testing environment by resetting digitization records and disabling tracking.
        """
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.Model = cls.env['invoice.digitization']
        cls.Model.search([]).unlink()

    def test_create_activation_logic(self):
        """
        Validate activation behavior during record creation.

        Expected behavior:
            - Creating an active configuration deactivates existing active records under the same account type.
            - Creating an inactive record does not affect other configurations.
            - Configurations for different account types do not interfere with each other.
        """
        config1 = self.Model.create({
            'name': 'Config 1',
            'account_type': 'out_invoice',
            'active_configuration': True,
        })
        self.assertTrue(config1.active_configuration)

        config2 = self.Model.create({
            'name': 'Config 2',
            'account_type': 'out_invoice',
            'active_configuration': True,
        })
        self.assertTrue(config2.active_configuration)
        self.assertFalse(config1.browse(config1.id).active_configuration)

        config3 = self.Model.create({
            'name': 'Config 3',
            'account_type': 'out_invoice',
            'active_configuration': False,
        })
        self.assertTrue(config2.browse(config2.id).active_configuration)
        self.assertFalse(config3.active_configuration)

        config_vendor = self.Model.create({
            'name': 'Vendor Config',
            'account_type': 'in_invoice',
            'active_configuration': True,
        })
        self.assertTrue(config_vendor.active_configuration)
        self.assertTrue(config2.browse(config2.id).active_configuration)

    def test_write_activation_logic(self):
        """
        Validate activation behavior when modifying records using `write()`.

        Expected behavior:
            - Updating active status should switch activation to the updated record.
            - Updating any other field should not impact active configuration.
            - Activation changes remain isolated by account type.
        """
        config1 = self.Model.create({
            'name': 'Config 1',
            'account_type': 'out_invoice',
            'active_configuration': True,
        })
        config2 = self.Model.create({
            'name': 'Config 2',
            'account_type': 'out_invoice',
            'active_configuration': False,
        })

        config2.write({'active_configuration': True})

        self.assertTrue(config2.browse(config2.id).active_configuration)
        self.assertFalse(config1.browse(config1.id).active_configuration)

        config2.write({'name': 'Updated Name'})
        self.assertTrue(config2.active_configuration)
        self.assertFalse(config1.active_configuration)

        vendor1 = self.Model.create({
            'name': 'Vendor Config 1',
            'account_type': 'in_invoice',
            'active_configuration': False,
        })
        vendor2 = self.Model.create({
            'name': 'Vendor Config 2',
            'account_type': 'in_invoice',
            'active_configuration': False,
        })

        vendor2.write({'active_configuration': True})

        self.assertTrue(vendor2.browse(vendor2.id).active_configuration)
        self.assertFalse(vendor1.browse(vendor1.id).active_configuration)

        self.assertTrue(config2.browse(config2.id).active_configuration)
