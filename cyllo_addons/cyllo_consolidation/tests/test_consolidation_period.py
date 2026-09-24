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
from . common import TestCommon
from odoo.exceptions import ValidationError


class TestConsolidationPeriod(TestCommon):
    """Test methods of the Consolidation Period"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.cons_chart.company_ids = cls.env.company.ids
        cls.cons_period.journal_ids = cls.cons_journal.ids

    def test_create(self):
        cons_period = self.cons_period
        cons_period.create({'chart_id': self.cons_chart.id,
                            'state': 'draft',
                            'start_date': '2000-1-1',
                            'end_date': '2000-1-10',})
        latest_period = self.env['consolidation.period'].search([], order='id desc', limit=1)
        self.assertEqual(latest_period.company_period_ids.company_id.ids,  latest_period.chart_id.company_ids.ids)
        self.assertEqual(latest_period.company_period_ids.period_id,  latest_period)
        self.assertEqual(latest_period.company_period_ids.start_date,  latest_period.start_date)
        self.assertEqual(latest_period.company_period_ids.end_date,  latest_period.end_date)

    def test_compute_dates(self):
        cons_period = self.cons_period
        cons_period._compute_dates()
        self.assertEqual(cons_period.dates, cons_period.start_date.strftime('%b %Y'))
        cons_period.end_date = '2000-2-10'
        cons_period._compute_dates()
        self.assertEqual(cons_period.dates,  f"{cons_period.start_date.strftime('%b %Y')} - {cons_period.end_date.strftime('%b %Y')}")
   
    def test_compute_account_ids_count(self):
        cons_period = self.cons_period
        cons_period._compute_account_ids_count()
        self.assertEqual(cons_period.account_ids_count, cons_period.chart_id.account_ids_count)

    def test_compute_journal_ids_count(self):
        cons_period = self.cons_period
        cons_period._compute_journal_ids_count()
        self.assertEqual(cons_period.journal_ids_count, len(cons_period.journal_ids))

    def test_compute_total_amount(self):
        cons_period = self.cons_period
        cons_period._compute_total_amount()
        self.assertEqual(cons_period.total_amount, sum(cons_period.journal_ids.journal_line_ids.mapped('balance')))

    def test_action_close(self):
        cons_period = self.cons_period
        cons_period.action_close()
        self.assertEqual(cons_period.state, 'closed')

    def test_action_draft(self):
        cons_period = self.cons_period
        cons_period.action_draft()
        self.assertEqual(cons_period.state, 'draft')

    def test_check_start_date(self):
        cons_period = self.cons_period
        cons_period._check_start_date()
        with self.assertRaises(ValidationError):
            cons_period.start_date = '2000-3-10'

    def test_action_open_accounts(self):
        cons_period = self.cons_period
        self.assertEqual(cons_period.action_open_accounts(), {
            'type': 'ir.actions.act_window',
            'name': 'Consolidation Accounts',
            'view_mode': 'tree,form',
            'res_model': 'consolidation.account',
            'target': 'current',
            'domain': [('chart_id', '=', self.cons_period.chart_id.id)],
            'context': {'default_chart_id': self.cons_period.chart_id.id},
        })

    def test_action_state(self):
        cons_period = self.cons_period
        cons_period.action_state()

    def test_action_create_journal(self):
        cons_period = self.cons_period
        cons_period.action_create_journal()
        self.assertEqual(cons_period.company_period_ids.company_id, cons_period.chart_id.company_ids)
        self.assertEqual(cons_period.company_period_ids.period_id, cons_period)
        self.assertEqual(cons_period.company_period_ids.start_date, cons_period.start_date)
        self.assertEqual(cons_period.company_period_ids.end_date, cons_period.end_date)
        journal_id = self.cons_period.journal_ids.search([('period_id', '=', cons_period.id), ('company_id', '=', cons_period.chart_id.company_ids.id)])
        self.assertEqual(journal_id.journal_line_ids.journal_id, journal_id)
        self.assertEqual(journal_id.journal_line_ids.group_id, cons_period.chart_id.account_ids.group_id)
        self.assertEqual(journal_id.journal_line_ids.account_id, cons_period.chart_id.account_ids)
        self.assertEqual(journal_id.journal_line_ids.balance, 0)

    def test_action_open_journals(self):
        cons_period = self.cons_period
        self.assertEqual(cons_period.action_open_journals(), {
            'type': 'ir.actions.act_window',
            'name': 'Consolidated Journals',
            'view_mode': 'tree,form',
            'res_model': 'consolidation.journal',
            'target': 'current',
            'domain': [('period_id', '=', self.cons_period.id)],
            'context': {'create': False, 'edit': False},
        })

    def test_get_filter(self):
        period_id = self.cons_period
        period_ids = self.env['consolidation.period'].search([('chart_id', '=', period_id.chart_id.id)])
        self.assertEqual(period_id.get_filter(period_id), {
            'journal': [(journal_id.id, journal_id.name) for journal_id in period_id.journal_ids],
            'comparison': [(pid.id, f'{pid.chart_id.name} ({pid.dates})')
                           for pid in period_ids if pid.id != period_id.id and pid.journal_ids]
        })