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
"""Catch me up and the activity digest only ever expose what the asking
user may read: record rules, access rights and app access all apply."""
import json
from unittest.mock import patch

from odoo import fields
from odoo.exceptions import AccessError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase, new_test_user

LLM_PATH = 'odoo.addons.cyllo_ai.models.cyllo_ai_briefing.LLMClient'
SALESMAN = 'base.group_user,sales_team.group_sale_salesman'


@tagged('post_install', '-at_install')
class TestAiAccess(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['cyllo.ai.config'].search([]).write({'is_active': False})
        groups = SALESMAN + (',project.group_project_user' if 'project.project' in cls.env else '')
        cls.user_a = new_test_user(cls.env, login='cmu_sales_a', groups=groups)
        cls.user_b = new_test_user(cls.env, login='cmu_sales_b', groups=groups)
        cls.customer = cls.env['res.partner'].create({
            'name': 'Access Traders', 'is_company': True, 'customer_rank': 1})
        cls.contact = cls.env['res.partner'].create({
            'name': 'Access Buyer', 'parent_id': cls.customer.id, 'email': 'buyer@access.test'})
        product = cls.env['product.product'].create({'name': 'Access Paper', 'type': 'consu'})
        cls.order_a = cls._order(product, cls.user_a, 1000.0)
        cls.order_b = cls._order(product, cls.user_b, 9000.0)
        for order in (cls.order_a, cls.order_b):
            order.message_post(body='Please send a revised price for %s' % order.name,
                               author_id=cls.contact.id, message_type='comment',
                               subtype_xmlid='mail.mt_comment')
        cls.lead_b = None
        if 'crm.lead' in cls.env:
            cls.lead_b = cls.env['crm.lead'].create({
                'name': 'Secret deal of B', 'type': 'opportunity', 'partner_id': cls.customer.id,
                'user_id': cls.user_b.id, 'expected_revenue': 50000})
            cls.lead_b.activity_schedule('mail.mail_activity_data_todo', user_id=cls.user_b.id,
                                         summary='B private follow-up')

    @classmethod
    def _order(cls, product, user, price):
        order = cls.env['sale.order'].create({
            'partner_id': cls.contact.id, 'user_id': user.id,
            'order_line': [(0, 0, {'product_id': product.id, 'product_uom_qty': 1,
                                   'price_unit': price, 'tax_id': [(5, 0, 0)]})],
        })
        order.action_confirm()
        return order

    def _brief(self, user):
        return self.env['cyllo.ai.briefing'].with_user(user).get_briefing(
            'res.partner', self.customer.id)

    @staticmethod
    def _record_links(brief):
        links = [k['link'] for k in brief['kpis']] + [r['link'] for r in brief['risks']]
        links += [row['link'] for s in brief['sections'] for row in s['rows']]
        return [(l['res_model'], l['res_id']) for l in links if l.get('res_id')]

    def test_every_link_points_to_a_record_the_user_can_read(self):
        brief = self._brief(self.user_a)
        links = self._record_links(brief)
        self.assertTrue(links)
        for model, res_id in links:
            record = self.env[model].with_user(self.user_a).browse(res_id)
            record.check_access_rights('read')
            record.check_access_rule('read')

    def test_salesperson_sees_only_own_orders_and_their_messages(self):
        brief = self._brief(self.user_a)
        links = self._record_links(brief)
        self.assertIn(('sale.order', self.order_a.id), links)
        self.assertNotIn(('sale.order', self.order_b.id), links)
        sales = next(k for k in brief['kpis'] if k['key'] == 'sales')
        self.assertNotIn('10,000', sales['value'])
        self.assertNotIn('9,000', json.dumps(brief))

        admin_links = self._record_links(self._brief(self.env.ref('base.user_admin')))
        self.assertIn(('sale.order', self.order_b.id), admin_links)

    def test_other_salespersons_leads_and_activities_are_hidden(self):
        if not self.lead_b:
            self.skipTest('crm is not installed')
        brief = self._brief(self.user_a)
        dumped = json.dumps(brief)
        self.assertNotIn('Secret deal of B', dumped)
        self.assertNotIn('B private follow-up', dumped)
        self.assertNotIn(('crm.lead', self.lead_b.id), self._record_links(brief))

        own = json.dumps(self._brief(self.user_b))
        self.assertIn('Secret deal of B', own)

    def test_ai_only_receives_the_users_own_data(self):
        with patch(LLM_PATH) as client:
            client.return_value.is_configured.return_value = True
            client.return_value.complete.return_value = '{"summary": "ok", "next_step": "go"}'
            self._brief(self.user_a)
            sent = client.return_value.complete.call_args[0][0][1]['content']
        self.assertIn(self.order_a.name, sent)
        self.assertNotIn(self.order_b.name, sent)
        self.assertNotIn('Secret deal of B', sent)

    def test_digest_counts_only_visible_records(self):
        today = str(fields.Date.context_today(self.env['cyllo.ai.digest']))
        Digest = self.env['cyllo.ai.digest']
        mine = Digest.with_user(self.user_a).get_digest(today, today)
        everyone = Digest.get_digest(today, today)

        def orders(digest):
            items = digest['apps'].get('Sales', []) if isinstance(digest['apps'], dict) else []
            return next((i['count'] for i in items if i['what'] == 'Sales orders confirmed'), 0)

        visible = self.env['sale.order'].with_user(self.user_a).search_count([
            ('state', '=', 'sale'), ('id', 'in', (self.order_a | self.order_b).ids)])
        self.assertEqual(visible, 1)
        self.assertLess(orders(mine), orders(everyone))

    def test_portal_users_are_refused(self):
        portal = new_test_user(self.env, login='cmu_portal', groups='base.group_portal')
        with self.assertRaises(AccessError):
            self.env['cyllo.ai.briefing'].with_user(portal).get_briefing(
                'res.partner', portal.partner_id.id)
        with self.assertRaises(AccessError):
            self.env['cyllo.ai.digest'].with_user(portal).get_digest('2026-01-01', '2026-01-07')

    def test_private_project_is_refused_to_non_members(self):
        if 'project.project' not in self.env:
            self.skipTest('project is not installed')
        project = self.env['project.project'].create({
            'name': 'Board-only project', 'privacy_visibility': 'followers'})
        with self.assertRaises(AccessError):
            self.env['cyllo.ai.briefing'].with_user(self.user_a).get_briefing(
                'project.project', project.id)
