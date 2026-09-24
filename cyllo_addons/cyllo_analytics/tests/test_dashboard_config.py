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
from odoo.exceptions import ValidationError


class TestDashboardConfig(TransactionCase):

    def setUp(self):
        super().setUp()

        self.DashboardConfig = self.env['dashboard.config']
        self.banner = self.env.ref('cyllo_analytics.dashboard_banner_no_banner')
        self.theme = self.env.ref('cyllo_analytics.dashboard_theme_cyllo')
        self.admin_group = self.env.ref(
            'cyllo_analytics.group_cyllo_analytics_admin'
        )

    def test_01_create_dashboard_config(self):
        """Test dashboard config creation with defaults"""
        dashboard = self.DashboardConfig.create({
            'name': 'Test Dashboard',
        })

        self.assertTrue(dashboard, "Dashboard config not created")
        self.assertEqual(dashboard.name, 'Test Dashboard')
        self.assertEqual(dashboard.banner_id.id, self.banner.id)
        self.assertEqual(dashboard.theme_id.id, self.theme.id)
        self.assertIn(
            self.admin_group,
            dashboard.group_ids,
            "Admin group not added by default"
        )

    def test_02_users_ids_computation(self):
        """Test users_ids computation includes admin users"""
        dashboard = self.DashboardConfig.create({
            'name': 'User Test Dashboard',
        })

        admin_users = self.admin_group.users

        self.assertTrue(
            dashboard.users_ids,
            "users_ids should not be empty"
        )

        for user in admin_users:
            self.assertIn(
                user,
                dashboard.users_ids,
                "Admin users must always be included"
            )

        self.assertIn(
            self.admin_group,
            dashboard.group_ids,
            "Admin group must be enforced"
        )

    def test_03_get_dashboard_data(self):
        """Test dashboard data structure"""
        dashboard = self.DashboardConfig.create({
            'name': 'Data Dashboard',
            'limit': 5,
        })

        data = dashboard.get_dashboard_data()

        self.assertIsInstance(data, dict)
        self.assertIn('sheets', data)
        self.assertIn('theme', data)
        self.assertEqual(data['name'], 'Data Dashboard')

    def test_04_prevent_main_dashboard_unlink(self):
        """Main dashboard should not be removable"""
        main_dashboard = self.env.ref(
            'cyllo_analytics.dashboard_config_main'
        )

        with self.assertRaises(ValidationError):
            main_dashboard.unlink()
