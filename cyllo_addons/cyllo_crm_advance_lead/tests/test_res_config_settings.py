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
class TestResConfigSettings(TransactionCase):
    """
    Test cases for CRM Lead related settings added in res.config.settings.

    This ensures that:
    - Values are stored and retrieved correctly from ir.config_parameter.
    - The onchange on 'group_use_lead' resets dependent fields properly.
    """

    @classmethod
    def setUpClass(cls):
        """
        Set up shared environment for all tests.

        - Assign the res.config.settings model to cls.Config.
        - Assign ir.config_parameter (with sudo) to cls.param for direct access.
        """
        super().setUpClass()
        cls.Config = cls.env['res.config.settings']
        cls.param = cls.env['ir.config_parameter'].sudo()

    def test_onchange_group_use_lead(self):
        """
        Test saving CRM settings and the onchange logic.

        Steps:
        1. Create a res.config.settings record with custom lead values.
        2. Execute it and verify that values are correctly stored in
           ir.config_parameter.
        3. Create another settings record with group_use_lead enabled
           and all booleans set to True.
        4. Simulate disabling group_use_lead and run the onchange.
        5. Assert that the dependent boolean fields (wishlist, abandoned
           cart, referral) are reset to False.
        """
        config = self.Config.create({
            'create_lead_wishlist': True,
            'wishlist_days': 7,
            'create_lead_abandoned_cart': True,
            'abandoned_cart_days': 5,
            'create_lead_referral': True,
        })
        config.execute()

        self.assertEqual(
            self.param.get_param('cyllo_crm_advance_lead.create_lead_wishlist'),
            'True',
        )
        self.assertEqual(
            self.param.get_param('cyllo_crm_advance_lead.wishlist_days'),
            '7',
        )
        self.assertEqual(
            self.param.get_param(
                'cyllo_crm_advance_lead.create_lead_abandoned_cart'),
            'True',
        )
        self.assertEqual(
            self.param.get_param('cyllo_crm_advance_lead.abandoned_cart_days'),
            '5',
        )
        self.assertEqual(
            self.param.get_param('cyllo_crm_advance_lead.create_lead_referral'),
            'True',
        )
        config = self.Config.create({
            'group_use_lead': True,
            'create_lead_wishlist': True,
            'create_lead_abandoned_cart': True,
            'create_lead_referral': True,
        })

        config.group_use_lead = False
        config._onchange_group_use_lead()

        self.assertFalse(config.create_lead_wishlist)
        self.assertFalse(config.create_lead_abandoned_cart)
        self.assertFalse(config.create_lead_referral)
