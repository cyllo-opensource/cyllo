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


class TestAccountMove(common.TransactionCase):

    def setUp(self):
        super().setUp()



        self.env['ir.config_parameter'].sudo().set_param(
            'cyllo_intercompany_transfer.create_vendor_bills',
            True
        )


    def test_vendor_bill_setting_enabled(self):
        """Verify vendor bill creation setting is enabled."""
        self.assertEqual(
            self.env['ir.config_parameter'].sudo().get_param(
                'cyllo_intercompany_transfer.create_vendor_bills'
            ),
            'True'
        )

    def test_account_move_has_action_post(self):
        """Verify action_post method exists on account.move."""
        self.assertTrue(
            hasattr(self.env['account.move'], 'action_post')
        )