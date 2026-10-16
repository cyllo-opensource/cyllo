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
"""Tests for the activity digest (cyllo.ai.digest + activity_digest tool)."""
from datetime import timedelta
from urllib.parse import parse_qs

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase, new_test_user

from odoo.addons.cyllo_ai.core.tools.base import ToolContext
from odoo.addons.cyllo_ai.core.tools.builtins import DEFAULT_TOOL_CLASSES
from odoo.addons.cyllo_ai.core.tools.digest import ActivityDigestTool


@tagged('post_install', '-at_install')
class TestDigest(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Digest = cls.env['cyllo.ai.digest']
        cls.today = fields.Date.context_today(cls.Digest)
        partner = cls.env['res.partner'].create({'name': 'Digest Customer'})
        product = cls.env['product.product'].create({'name': 'Digest Item', 'type': 'consu'})
        cls.order = cls.env['sale.order'].create({
            'partner_id': partner.id,
            'order_line': [(0, 0, {'product_id': product.id, 'product_uom_qty': 1,
                                   'price_unit': 500.0, 'tax_id': [(5, 0, 0)]})],
        })
        cls.order.action_confirm()

    def _metric(self, digest, key_label):
        for items in digest['apps'].values():
            for item in items:
                if item['what'] == key_label:
                    return item
        return None

    def test_week_digest_counts_and_links_confirmed_orders(self):
        digest = self.Digest.get_digest(str(self.today - timedelta(days=6)), str(self.today))
        item = self._metric(digest, 'Sales orders confirmed')
        self.assertTrue(item)
        self.assertGreaterEqual(item['count'], 1)
        self.assertIn('amount', item)
        self.assertTrue(item['link'].startswith('/web#cyllo_digest=sale_orders&'))
        self.assertIn('answer_style', digest)

        params = parse_qs(item['link'].split('#', 1)[1])
        action = self.Digest.get_metric_action(
            params['cyllo_digest'][0], params['from'][0], params['to'][0])
        self.assertEqual(action['res_model'], 'sale.order')
        self.assertIn(self.order, self.env['sale.order'].search(action['domain']))

    def test_purchases_follow_order_date_and_total_like_the_purchase_app(self):
        if 'purchase.order' not in self.env:
            self.skipTest('purchase is not installed')
        vendor = self.env['res.partner'].create({'name': 'Digest Vendor'})
        product = self.env['product.product'].create({'name': 'Digest Part', 'type': 'consu'})
        order = self.env['purchase.order'].create({
            'partner_id': vendor.id,
            'order_line': [(0, 0, {'product_id': product.id, 'product_qty': 1,
                                   'price_unit': 700.0, 'taxes_id': [(5, 0, 0)]})],
        })
        order.button_confirm()
        order.write({'date_order': fields.Datetime.to_datetime('1990-03-10 10:00:00'),
                     'date_approve': fields.Datetime.to_datetime('1990-04-10 10:00:00')})
        digest = self.Digest.get_digest('1990-03-01', '1990-03-31')
        item = self._metric(digest, 'Purchase orders confirmed')
        self.assertEqual(item['count'], 1)
        self.assertIn('700', item['amount'])

    def test_leads_and_opportunities_are_counted_like_their_menus(self):
        if 'crm.lead' not in self.env:
            self.skipTest('crm is not installed')
        Lead = self.env['crm.lead']
        Lead.create([{'name': 'Digest lead', 'type': 'lead'},
                     {'name': 'Digest lead 2', 'type': 'lead'},
                     {'name': 'Digest opportunity', 'type': 'opportunity'}])
        digest = self.Digest.get_digest(str(self.today), str(self.today))
        leads_domain = ['|', ('type', '=', 'lead'), ('type', '=', False)]
        today_domain = [('create_date', '>=', fields.Datetime.to_string(
            fields.Datetime.now() - timedelta(days=1)))]
        self.assertEqual(self._metric(digest, 'Leads created')['count'],
                         Lead.search_count(leads_domain + today_domain))
        self.assertEqual(self._metric(digest, 'Opportunities created')['count'],
                         Lead.search_count([('type', '=', 'opportunity')] + today_domain))

    def test_empty_period_says_nothing_happened(self):
        digest = self.Digest.get_digest('1990-01-01', '1990-01-07')
        self.assertIsInstance(digest['apps'], str)

    def test_reversed_dates_are_swapped_and_long_periods_refused(self):
        digest = self.Digest.get_digest(str(self.today), str(self.today - timedelta(days=6)))
        self.assertTrue(self._metric(digest, 'Sales orders confirmed'))
        with self.assertRaises(UserError):
            self.Digest.get_digest('2020-01-01', str(self.today))
        with self.assertRaises(UserError):
            self.Digest.get_digest('not a date', str(self.today))

    def test_unknown_metric_link_is_refused(self):
        with self.assertRaises(UserError):
            self.Digest.get_metric_action('nope', str(self.today), str(self.today))

    def test_apps_the_user_cannot_read_are_left_out(self):
        user = new_test_user(self.env, login='digest_basic', groups='base.group_user')
        digest = self.Digest.with_user(user).get_digest(str(self.today), str(self.today))
        apps = digest['apps'] if isinstance(digest['apps'], dict) else {}
        self.assertNotIn('Sales', apps)
        self.assertNotIn('Invoicing', apps)

    def test_tool_is_registered_and_runs(self):
        self.assertIn(ActivityDigestTool, DEFAULT_TOOL_CLASSES)
        out = ActivityDigestTool().run(ToolContext(env=self.env),
                                       date_from=str(self.today), date_to=str(self.today))
        self.assertTrue(self._metric(out, 'Sales orders confirmed'))
