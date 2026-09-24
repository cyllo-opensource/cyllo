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


class TestDashboardConfigMenu(TransactionCase):

    def setUp(self):
        super().setUp()
        self.DashboardConfigMenu = self.env['dashboard.config.menu']
        self.parent_menu = self.env.ref('base.menu_administration')

    def test_create_dashboard_config_menu_wizard(self):
        """Test dashboard config menu wizard creation"""
        wizard = self.DashboardConfigMenu.create({
            'name': 'Test Dashboard Menu',
            'menu_id': self.parent_menu.id,
        })

        self.assertTrue(wizard, "Wizard record was not created")
        self.assertEqual(
            wizard.name,
            'Test Dashboard Menu',
            "Wizard name not set correctly"
        )
        self.assertEqual(
            wizard.menu_id.id,
            self.parent_menu.id,
            "Parent menu not assigned correctly"
        )
