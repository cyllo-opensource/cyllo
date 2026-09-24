# -*- coding: utf-8 -*-
#############################################################################
#
#    Cyllo Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cyllo(<https://www.cyllo.com>)
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
from odoo.tests import TransactionCase, tagged
from unittest.mock import patch, MagicMock

@tagged('-at_install', 'post_install')
class TestDashboardAlert(TransactionCase):

    def setUp(self):
        super(TestDashboardAlert, self).setUp()
        self.alert_model = self.env['dashboard.alert']
        
        # Create a mock dashboard sheet to associate with alerts
        self.sheet = self.env['dashboard.sheet'].create({
            'name': 'Test Sheet',
            'query': 'SELECT * FROM mock_table',
        })
        
        # Mock user to receive alerts
        self.test_user = self.env.user
        self.test_user.email = 'test@example.com'

    def test_legacy_alert_evaluation_triggered(self):
        """Test the legacy single-condition alert when condition is met."""
        alert = self.alert_model.create({
            'name': 'Sales Alert (Legacy)',
            'sheet_id': self.sheet.id,
            'user_id': self.test_user.id,
            'condition': 'gt',
            'value': 1000.0,
            'send_email': False,
        })
        
        self.sheet.query = "SELECT 1500.0 AS mock_measure"
             
        alert._evaluate_alert()
        self.assertTrue(alert.is_condition_met)

    def test_legacy_alert_evaluation_not_triggered(self):
        """Test the legacy alert when condition is NOT met."""
        alert = self.alert_model.create({
            'name': 'Sales Alert (Legacy Below)',
            'sheet_id': self.sheet.id,
            'user_id': self.test_user.id,
            'condition': 'gt',
            'value': 1000.0,
        })
        
        self.sheet.query = "SELECT 500.0 AS mock_measure"
             
        alert._evaluate_alert()
        self.assertFalse(alert.is_condition_met)

    def test_multi_measure_alert_triggered(self):
        """Test multi-measure alert evaluation."""
        alert = self.alert_model.create({
            'name': 'Multi-Measure Alert',
            'sheet_id': self.sheet.id,
            'user_id': self.test_user.id,
            'condition_ids': [
                (0, 0, {
                    'measure_alias': 'sales',
                    'measure_label': 'Total Sales',
                    'condition': 'lt',
                    'value': 500.0,
                }),
                (0, 0, {
                    'measure_alias': 'costs',
                    'measure_label': 'Total Costs',
                    'condition': 'gt',
                    'value': 200.0,
                })
            ]
        })
        
        # Row meets BOTH conditions
        self.sheet.query = "SELECT 400.0 AS sales, 300.0 AS costs"
             
        alert._evaluate_alert()
        
        # Both conditions should be marked as met
        for cond in alert.condition_ids:
            self.assertTrue(cond.is_met)

    def test_multi_measure_alert_partial_trigger(self):
        """Test multi-measure alert where only ONE condition is met."""
        alert = self.alert_model.create({
            'name': 'Partial Multi-Measure Alert',
            'sheet_id': self.sheet.id,
            'user_id': self.test_user.id,
            'condition_ids': [
                (0, 0, {
                    'measure_alias': 'sales',
                    'measure_label': 'Total Sales',
                    'condition': 'lt',
                    'value': 500.0,
                }),
                (0, 0, {
                    'measure_alias': 'costs',
                    'measure_label': 'Total Costs',
                    'condition': 'gt',
                    'value': 200.0,
                })
            ]
        })
        
        # Row meets only the costs condition (costs > 200), sales is NOT < 500
        self.sheet.query = "SELECT 600.0 AS sales, 300.0 AS costs"
             
        alert._evaluate_alert()
        
        sales_cond = alert.condition_ids.filtered(lambda c: c.measure_alias == 'sales')
        costs_cond = alert.condition_ids.filtered(lambda c: c.measure_alias == 'costs')
        
        self.assertFalse(sales_cond.is_met)
        self.assertTrue(costs_cond.is_met)

    def test_dimension_filter_alert(self):
        """Test dimension-level filtering."""
        alert = self.alert_model.create({
            'name': 'Dimension Filter Alert',
            'sheet_id': self.sheet.id,
            'user_id': self.test_user.id,
            'dimension_filter': True,
            'dimension_alias': 'customer',
            'dimension_value': 'VIP',
            'condition_ids': [
                (0, 0, {
                    'measure_alias': 'sales',
                    'condition': 'gt',
                    'value': 1000.0,
                })
            ]
        })
        
        # Row 1 exceeds threshold but is NOT the VIP customer
        # Row 2 is VIP customer but does NOT exceed threshold
        self.sheet.query = "SELECT 'Regular' AS customer, 2000.0 AS sales UNION ALL SELECT 'VIP' AS customer, 500.0 AS sales"
             
        alert._evaluate_alert()
        
        # Should NOT trigger because VIP's sales are below 1000
        self.assertFalse(alert.condition_ids[0].is_met)
            
        # Now change VIP sales to exceed threshold
        self.sheet.query = "SELECT 'Regular' AS customer, 2000.0 AS sales UNION ALL SELECT 'VIP' AS customer, 1500.0 AS sales"
             
        alert._evaluate_alert()
        
        self.assertTrue(alert.condition_ids[0].is_met)

    def test_send_notification_logic(self):
        """Verify that _send_notification creates mail.message and mail.notification records."""
        alert = self.alert_model.create({
            'name': 'Notify Test Alert',
            'sheet_id': self.sheet.id,
            'user_id': self.test_user.id,
            'screen_notification': True,
            'send_email': True,
        })
        
        initial_msg_count = self.env['mail.message'].search_count([])
        initial_notif_count = self.env['mail.notification'].search_count([])
        
        # Ensure odoobot exists
        if not self.env.ref('base.partner_root', raise_if_not_found=False):
            self.env['res.partner'].create({'name': 'OdooBot'})
             
        alert._send_notification("Test summary triggered")
            
        # Verify inbox message was created
        self.assertGreater(
            self.env['mail.message'].search_count([]),
            initial_msg_count,
            "Expected a new mail.message to be created after _send_notification"
        )
        
        # Verify at least one mail.notification was created for the recipient
        self.assertGreater(
            self.env['mail.notification'].search_count([]),
            initial_notif_count,
            "Expected a new mail.notification to be created for the alert recipient"
        )
