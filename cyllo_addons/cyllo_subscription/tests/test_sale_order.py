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
import logging

from dateutil.relativedelta import relativedelta

from odoo import _, fields
from odoo.exceptions import ValidationError
from odoo.addons.cyllo_subscription.tests.common import TestCylloSubscription

_logger = logging.getLogger(__name__)

class TestSaleOrder(TestCylloSubscription):

    def test_action_confirm(self):
        _logger.info("Starts test_action_confirm")
        self.sale_order3.order_line.create({
            'order_id': self.sale_order3.id,
            'product_id': self.subscription_product1.id,
            'product_uom_qty': 1,
            'price_unit': 50.0,
            'time_based_price_id': self.time_based.id,
            'trial_end': '2025-11-30',
        })
        initial_subscription_order_count = self.env['subscription.order'].search_count([])
        self.sale_order3.action_confirm()
        self.assertEqual(self.env['subscription.order'].search_count([]), initial_subscription_order_count + 1,
                         "Number of subscription order remains same.")
        with self.assertRaises(ValidationError):
            self.sale_order4.action_confirm()
        _logger.info("Ends test_action_confirm")

    def test_onchange_sale_order_template_id(self):
        _logger.info("Starts test_onchange_sale_order_template_id")
        renewal_date = (fields.Datetime.now() +
                        relativedelta(**{self.time_based.subscription_unit: self.time_based.duration}))
        self.sale_order5._onchange_sale_order_template_id()
        self.assertEqual(self.sale_order5.order_line.renewal_date, renewal_date,
                         "Error in test_onchange_sale_order_template_id")
        _logger.info("Ends test_onchange_sale_order_template_id")

    def test_compute_subscription_orders(self):
        _logger.info("Starts test_compute_subscription_orders")
        self.sale_order5._compute_subscription_orders()
        self.assertEqual(self.sale_order5.state_subscription, 'sub_order',
                         "Error in test_compute_subscription_orders")
        _logger.info("Ends test_compute_subscription_orders")

    def test_action_subscriptions(self):
        _logger.info("Starts test_action_subscriptions")
        subscription_orders = self.env['subscription.order'].search([('sale_order_id', '=', self.sale_order5.id)])
        self.assertEqual(self.sale_order5.action_subscriptions(), {
            'type': 'ir.actions.act_window',
            'name': _('Subscription Orders'),
            'res_model': 'subscription.order',
            'view_mode': 'tree,form',
            'target': 'current',
            'domain': [('id', 'in', subscription_orders.ids)]
        },
        "Error in test_action_subscriptions")
        _logger.info("Ends test_action_subscriptions")
