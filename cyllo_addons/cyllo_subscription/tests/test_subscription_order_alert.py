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
from datetime import date
from odoo.tests import common


class TestSubscriptionOrderAlert(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Create test data
        cls.company = cls.env.company
        cls.partner = cls.env['res.partner'].create({'name': 'Test Partner'})
        cls.currency = cls.company.currency_id

        cls.product = cls.env['product.template'].create({
            'name': 'Subscription Product',
            'is_subscription': True
        })

        cls.plan = cls.env['sale.order.template'].create({
            'name': 'Test Subscription Plan',
            'is_subscription': True
        })

        cls.order = cls.env['subscription.order'].create({
            'name': 'SO001',
            'partner_id': cls.partner.id,
            'sale_order_template_id': cls.plan.id,
            'state': 'draft',
            'recurring_revenue': 100.0
        })

        cls.alert = cls.env['subscription.order.alert'].create({
            'name': 'Test Alert',
            'monthly_recurrence_min': 50.0,
            'monthly_recurrence_max': 150.0,
            'state_of_order': 'draft',
            'subscription_plan_ids': [(4, cls.plan.id)],
            'subscription_products_ids': [(4, cls.product.id)],
            'partner_ids': [(4, cls.partner.id)],
            'action': 'set_to_renew'
        })

        cls.activity_type = cls.env['mail.activity.type'].create({'name': 'Test Activity Type'})
        cls.alert_with_activity = cls.env['subscription.order.alert'].create({
            'name': 'Test Alert Activity',
            'action': 'create_next_activity',
            'activity_type_id': cls.activity_type.id,
            'summary': 'Test Activity',
            'note': '<p>Test note</p>',
            'dead_line': date.today()
        })

    def test_filter_records(self):
        """Test the filter_records method."""
        domain = self.alert.filter_records()
        expected_domain = [
            ('recurring_revenue', '>=', 50.0),
            ('recurring_revenue', '<=', 150.0),
            ('sale_order_template_id', 'in', [self.plan.id]),
            ('state', '=', 'draft'),
            ('partner_id', 'in', [self.partner.id])
        ]
        self.assertEqual(domain, expected_domain, "Domain should match the expected filter conditions.")

    def test_action_trigger(self):
        """Test action_trigger method"""
        self.alert.action_trigger()
        self.assertEqual(self.order.state_subscription, 'renew', "Order state should be set to 'renew'.")
        self.alert_with_activity.action_trigger()
        activity = self.env['mail.activity'].search([('summary', '=', 'Test Activity')], limit=1)
        self.assertTrue(activity, "Activity should be created.")
        self.assertEqual(activity.note, '<p>Test note</p>', "Activity note should match.")
        self.assertEqual(activity.date_deadline, date.today(), "Deadline should be set correctly.")

