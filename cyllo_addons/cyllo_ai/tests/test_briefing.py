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
"""Tests for the Catch me up briefing (cyllo.ai.briefing)."""
import json
from datetime import date, datetime, timedelta
from unittest.mock import patch

from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase, new_test_user

LLM_PATH = 'odoo.addons.cyllo_ai.models.cyllo_ai_briefing.LLMClient'


@tagged('post_install', '-at_install')
class TestBriefing(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['cyllo.ai.config'].search([]).write({'is_active': False})
        cls.Briefing = cls.env['cyllo.ai.briefing']
        cls.today = fields.Date.context_today(cls.Briefing)
        cls.company = cls.env['res.partner'].create({
            'name': 'Malabar Traders', 'is_company': True, 'customer_rank': 1})
        cls.contact = cls.env['res.partner'].create({
            'name': 'Purchase Head', 'parent_id': cls.company.id, 'email': 'head@malabar.test'})
        cls.product = cls.env['product.product'].create({
            'name': 'A4 Paper', 'type': 'consu', 'list_price': 100.0})

    def _invoice(self, due, amount=1000.0):
        move = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.company.id,
            'invoice_date': due - timedelta(days=30),
            'invoice_date_due': due,
            'invoice_line_ids': [(0, 0, {'product_id': self.product.id, 'quantity': 1,
                                         'price_unit': amount, 'tax_ids': [(5, 0, 0)]})],
        })
        move.action_post()
        move.invoice_date_due = due
        return move

    def _order(self, when, amount):
        order = self.env['sale.order'].create({
            'partner_id': self.contact.id,
            'order_line': [(0, 0, {'product_id': self.product.id, 'product_uom_qty': 1,
                                   'price_unit': amount, 'tax_id': [(5, 0, 0)]})],
        })
        order.action_confirm()
        order.date_order = when
        return order

    def test_overdue_invoice_is_a_high_risk_with_link(self):
        invoice = self._invoice(self.today - timedelta(days=47))
        brief = self.Briefing.get_briefing('res.partner', self.contact.id)

        self.assertEqual(brief['title'], self.company.display_name)
        self.assertEqual(brief['source'], 'rules')
        risk = brief['risks'][0]
        self.assertEqual(risk['severity'], 'high')
        self.assertIn('47', risk['text'])
        self.assertEqual(risk['link']['res_model'], 'account.move')
        self.assertIn(invoice.id, risk['link']['domain'][0][2])
        self.assertEqual(brief['next_step'], risk['next_step'])
        receivable = next(k for k in brief['kpis'] if k['key'] == 'receivable')
        self.assertEqual(receivable['tone'], 'danger')
        rows = next(s for s in brief['sections'] if s['key'] == 'invoices_out')['rows']
        self.assertEqual(rows[0]['link'], {'res_model': 'account.move', 'res_id': invoice.id})

    def test_falling_orders_are_flagged(self):
        q_start = date(self.today.year, 3 * ((self.today.month - 1) // 3) + 1, 1)
        prev_start = q_start - relativedelta(months=3)
        self._order(datetime.combine(prev_start, datetime.min.time()), 6000.0)
        self._order(fields.Datetime.now(), 1000.0)
        brief = self.Briefing.get_briefing('res.partner', self.company.id)

        sales = next(k for k in brief['kpis'] if k['key'] == 'sales')
        self.assertEqual(sales['tone'], 'danger')
        self.assertTrue(any('down 83' in r['text'] for r in brief['risks']))

    def test_nothing_urgent_gives_a_calm_briefing(self):
        brief = self.Briefing.get_briefing('res.partner', self.company.id)
        self.assertEqual(brief['risks'], [])
        self.assertTrue(brief['summary'])
        self.assertTrue(brief['next_step'])

    def test_ai_narrative_is_used_when_configured(self):
        self._invoice(self.today - timedelta(days=10))
        reply = json.dumps({'summary': '1 invoice is overdue.', 'next_step': 'Call accounts.',
                            'mood': 'negative', 'mood_reason': 'Complained about delivery'})
        with patch(LLM_PATH) as client:
            client.return_value.is_configured.return_value = True
            client.return_value.complete.return_value = '```json\n%s\n```' % reply
            brief = self.Briefing.get_briefing('res.partner', self.company.id)
            facts = json.loads(client.return_value.complete.call_args[0][0][1]['content'])

        self.assertEqual(brief['source'], 'ai')
        self.assertEqual(brief['summary'], '1 invoice is overdue.')
        self.assertEqual(brief['next_step'], 'Call accounts.')
        self.assertEqual(brief['mood'], 'negative')
        self.assertTrue(facts['risks'])
        self.assertNotIn('role', brief)

    def test_ai_failure_falls_back_to_rules(self):
        self._invoice(self.today - timedelta(days=10))
        with patch(LLM_PATH) as client:
            client.return_value.is_configured.return_value = True
            client.return_value.complete.side_effect = UserError('provider down')
            brief = self.Briefing.get_briefing('res.partner', self.company.id)

        self.assertEqual(brief['source'], 'rules')
        self.assertTrue(brief['notice'])
        self.assertEqual(brief['next_step'], brief['risks'][0]['next_step'])

    def test_user_without_accounting_rights_gets_partial_briefing(self):
        self._invoice(self.today - timedelta(days=47))
        user = new_test_user(self.env, login='cmu_basic', groups='base.group_user')
        brief = self.Briefing.with_user(user).get_briefing('res.partner', self.company.id)

        self.assertFalse(any(k['key'] == 'receivable' for k in brief['kpis']))
        self.assertFalse(any(r['link']['res_model'] == 'account.move' for r in brief['risks']))

    def test_unsupported_model_is_refused(self):
        with self.assertRaises(UserError):
            self.Briefing.get_briefing('res.users', self.env.uid)

    def test_lead_past_closing_date(self):
        if 'crm.lead' not in self.env:
            self.skipTest('crm is not installed')
        lead = self.env['crm.lead'].create({
            'name': 'A4 paper annual contract', 'type': 'opportunity',
            'partner_id': self.company.id, 'expected_revenue': 50000,
            'date_deadline': self.today - timedelta(days=5),
        })
        brief = self.Briefing.get_briefing('crm.lead', lead.id)

        self.assertEqual(brief['title'], lead.name)
        self.assertEqual(brief['risks'][0]['severity'], 'high')
        self.assertTrue(any(r['next_step'].startswith('Schedule') for r in brief['risks']))

    def test_project_with_late_tasks(self):
        if 'project.project' not in self.env:
            self.skipTest('project is not installed')
        project = self.env['project.project'].create({
            'name': 'Warehouse fit-out', 'partner_id': self.company.id})
        task = self.env['project.task'].create({
            'name': 'Install racks', 'project_id': project.id,
            'date_deadline': fields.Datetime.now() - timedelta(days=12)})
        brief = self.Briefing.get_briefing('project.project', project.id)

        tasks = next(k for k in brief['kpis'] if k['key'] == 'tasks')
        self.assertEqual(tasks['tone'], 'danger')
        self.assertTrue(any('Install racks' in r['text'] for r in brief['risks']))
        rows = next(s for s in brief['sections'] if s['key'] == 'tasks')['rows']
        self.assertEqual(rows[0]['link'], {'res_model': 'project.task', 'res_id': task.id})
