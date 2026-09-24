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
from odoo import fields
from odoo.exceptions import ValidationError
from odoo.addons.cyllo_subscription.tests.common import TestCylloSubscription

_logger = logging.getLogger(__name__)


class TestSubscriptionOrder(TestCylloSubscription):

    def test_compute_partner_street(self):
        _logger.info("Starts test_compute_partner_street")
        self.subscription_order1._compute_partner_street()
        self.assertEqual(self.subscription_order1.partner_street, f'{self.partner.street} {self.partner.street2}',
                         msg="test_compute_partner_street Failed")
        self.partner.street = ''
        self.subscription_order1._compute_partner_street()
        self.assertEqual(self.subscription_order1.partner_street, f' {self.partner.street2}',
                         msg="test_compute_partner_street Failed")
        self.partner.street = 'street1'
        self.partner.street2 = ''
        self.subscription_order1._compute_partner_street()
        self.assertEqual(self.subscription_order1.partner_street, f'{self.partner.street} ',
                         msg="test_compute_partner_street Failed")
        _logger.info("Ends test_compute_partner_street")

    def test_unlink(self):
        _logger.info("Starts test_unlink")
        with self.assertRaises(ValidationError):
            self.subscription_order2.unlink()
        with self.assertRaises(ValidationError):
            self.subscription_order3.unlink()
        _logger.info("Ends test_unlink")

    def test_compute_invoice_count(self):
        _logger.info("Starts test_compute_invoice_count")
        self.subscription_order1._compute_invoice_count()
        self.assertEqual(self.subscription_order1.invoice_count, 1)
        _logger.info("Ends test_compute_invoice_count")

    def test_action_post(self):
        _logger.info("Starts test_action_post")
        with self.assertRaises(ValidationError):
            self.subscription_order4.action_post()
        _logger.info("Ends test_action_post")

    def test_compute_recurring_revenue(self):
        _logger.info("Start tests compute_recurring_revenue")
        partner = self.env['res.partner'].create({'name': 'John'})
        product = self.env['product.product'].create({
            'name': 'SP1',
            'is_subscription': True
        })
        time_based = self.env['time.based.price'].create({
            'name': 'Mon',
            'subscription_unit': 'months',
            'currency_id': 1
        })
        subscription_order = self.env['subscription.order'].create({
            'name': 'SO001',
            'partner_id': partner.id,
            'time_based_price_id': time_based.id,
            'recurring_revenue': 1,
            'subscription_order_line_ids': [
                (fields.Command.create({'product_id': product.id}))]
        })
        subscription_order._compute_recurring_revenue()
        self.assertEqual(subscription_order.recurring_revenue, 0.0)
        _logger.info("End tests compute_recurring_revenue")

    def test_action_renew_order(self):
        _logger.info("Start test_action_renew_order")
        partner = self.env['res.partner'].create({'name': 'John'})
        product = self.env['product.product'].create({
            'name': 'SP1',
            'is_subscription': True
        })
        time_based = self.env['time.based.price'].create({
            'name': 'Mon',
            'subscription_unit': 'months',
            'currency_id': 1
        })
        subscription_order = self.env['subscription.order'].create({
            'name': 'SO001',
            'partner_id': partner.id,
            'time_based_price_id': time_based.id,
            'recurring_revenue': 1,
            'subscription_order_line_ids': [
                (fields.Command.create({'product_id': product.id}))]
        })
        subscription_order.action_renew_order()
        self.assertFalse(self.subscription_order1.check_upsell_renewal)
        _logger.info("End test_action_renew_order")

    def test_check_subscription_renewal(self):
        _logger.info("Start tests test_check_subscription_renewal")
        self.subscription_order1.check_subscription_renewal()
        self.assertEqual(self.subscription_order1.state_subscription, 'renew')
        _logger.info("End tests test_check_subscription_renewal")

    def test_action_upsell(self):
        _logger.info("Start tests test_action_upsell")
        self.subscription_order2.action_renew_order()
        self.assertTrue(self.subscription_order2.check_upsell_renewal)
        _logger.info("End tests test_action_upsell")

    # Test in account.move
    def test_ir_cron_action_post(self):
        _logger.info("Start tests test_ir_cron_action_post")
        self.account_move.ir_cron_action_post()
        self.assertEqual(self.account_move.state, 'posted')
        _logger.info("Ends tests test_ir_cron_action_post")

    # Test in sale.order
    def test_compute_is_subscription(self):
        """Testing if added product is subscription"""
        _logger.info("Start tests test_compute_is_subscription")
        self.sale_order._compute_is_subscription()
        self.assertEqual(self.sale_order.is_subscription, True)
        self.sale_order2._compute_is_subscription()
        self.assertEqual(self.sale_order2.is_subscription, False)
        _logger.info("Ends tests test_compute_is_subscription")

    def test_compute_subscription_orders(self):
        _logger.info("Starts tests test_compute_subscription_orders")
        self.sale_order._compute_subscription_orders()
        self.assertEqual(self.sale_order.subscription_orders, 1)
        self.assertEqual(self.sale_order.state_subscription, 'sub_order')
        _logger.info("Ends tests test_compute_subscription_orders")

    # Test in subscription.order.alert
    def test_compute_order_count(self):
        _logger.info("Starts tests test_compute_order_count")
        self.subscription_order_alert._compute_order_count()
        _logger.info("Ends tests test_compute_order_count")

    def test_action_trigger(self):
        _logger.info("Starts tests test_action_trigger")
        self.subscription_order_alert.action_trigger()
        self.assertEqual(self.subscription_order1.state_subscription, 'renew')
        _logger.info("Ends tests test_action_trigger")

    def test_action_close_subscription(self):
        _logger.info("Starts tests test_action_close_subscription")
        self.assertEqual(self.subscription_order2.action_close_subscription(), {
            'name': 'Close Reason',
            'type': 'ir.actions.act_window',
            'res_model': 'subscription.close',
            'view_mode': 'form',
            'context': {'default_subscription_order_id': self.subscription_order2.id},
            'target': 'new',
        })
        _logger.info("Ends tests test_action_close_subscription")
