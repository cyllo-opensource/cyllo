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


class TestDashboardGlobalFilter(TransactionCase):

    def setUp(self):
        super().setUp()
        self.DashboardGlobalFilter = self.env['dashboard.global.filter']
        self.DashboardConfig = self.env['dashboard.config']

    def test_create_dashboard_global_filter(self):
        """Test dashboard global filter creation"""
        dashboard = self.DashboardConfig.create({
            'name': 'Test Dashboard',
        })

        global_filter = self.DashboardGlobalFilter.create({
            'name': 'Test Filter',
            'dashboard_config_id': dashboard.id,
        })

        self.assertTrue(
            global_filter,
            "Dashboard global filter record not created"
        )
        self.assertEqual(
            global_filter.name,
            'Test Filter',
            "Global filter name not set correctly"
        )
        self.assertEqual(
            global_filter.dashboard_config_id.id,
            dashboard.id,
            "Dashboard config relation not set correctly"
        )
