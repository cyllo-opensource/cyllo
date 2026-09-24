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


class TestDashboardPresentation(TransactionCase):

    def setUp(self):
        super().setUp()
        self.DashboardPresentation = self.env['dashboard.presentation']

    def test_create_dashboard_presentation_wizard(self):
        """Test dashboard presentation wizard creation"""
        wizard = self.DashboardPresentation.create({
            'chart_data': {'labels': ['A', 'B'], 'values': [10, 20]},
            'type': 'bar',
            'style': 'default',
            'style_json': {'color': 'blue'},
            'theme': 'light',
            'theme_json': {'background': '#ffffff'},
            'auto_slide': True,
            'auto_slide_time': 5,
            'title_page': True,
            'title_page_heading': 'Dashboard Report',
            'title_page_subheading': 'Monthly Overview',
        })

        self.assertTrue(wizard, "Dashboard presentation wizard not created")
        self.assertEqual(wizard.type, 'bar')
        self.assertTrue(wizard.auto_slide)
        self.assertEqual(wizard.auto_slide_time, 5)
        self.assertEqual(
            wizard.title_page_heading,
            'Dashboard Report',
            "Title page heading not set correctly"
        )
        self.assertIsInstance(wizard.chart_data, dict)
        self.assertIsInstance(wizard.style_json, dict)
        self.assertIsInstance(wizard.theme_json, dict)
