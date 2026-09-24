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


class TestStockPicking(common.TransactionCase):

    def setUp(self):
        super().setUp()

        self.env['ir.config_parameter'].sudo().set_param(
            'cyllo_intercompany_transfer.synchronize_stock_moves',
            True
        )

    def test_intercompany_waiting_default(self):
        """Verify default value of intercompany_waiting field."""
        picking = self.env['stock.picking'].new({})

        self.assertFalse(
            picking.intercompany_waiting
        )

    def test_sync_setting_enabled(self):
        """Verify stock synchronization setting is enabled."""
        self.assertEqual(
            self.env['ir.config_parameter'].sudo().get_param(
                'cyllo_intercompany_transfer.synchronize_stock_moves'
            ),
            'True'
        )

    def test_stock_picking_has_sync_method(self):
        """Verify synchronization method exists."""
        self.assertTrue(
            hasattr(
                self.env['stock.picking'],
                '_sync_intercompany_receipt'
            )
        )

    def test_stock_picking_has_action_assign(self):
        """Verify action_assign override exists."""
        self.assertTrue(
            hasattr(
                self.env['stock.picking'],
                'action_assign'
            )
        )

    def test_stock_picking_has_button_validate(self):
        """Verify button_validate override exists."""
        self.assertTrue(
            hasattr(
                self.env['stock.picking'],
                'button_validate'
            )
        )