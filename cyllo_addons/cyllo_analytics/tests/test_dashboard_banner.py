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


class TestDashboardBanner(TransactionCase):

    def setUp(self):
        super().setUp()
        self.DashboardBanner = self.env['dashboard.banner']

    def test_create_dashboard_banner(self):
        """Test dashboard banner creation"""
        banner = self.DashboardBanner.create({
            'name': 'Test Banner',
        })

        self.assertTrue(banner, "Dashboard Banner record was not created")
        self.assertEqual(
            banner.name,
            'Test Banner',
            "Dashboard Banner name is not set correctly"
        )
