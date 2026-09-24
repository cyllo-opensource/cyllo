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
from .common import TestCommon


class TestConsolidationChart(TestCommon):
    """Test methods of the Consolidation Chart"""

    def test_compute_is_currency_different(self):
        cons_chart = self.cons_chart
        currency_object = self.env['res.currency'].create({
            'name': 'Test Currency',
            'symbol': 'TC',
            'rounding': 0.1,
        })
        cons_chart.currency_id = currency_object.id
        cons_chart.company_ids = self.env.company.ids
        cons_chart._compute_is_currency_different()
        self.assertEqual(cons_chart.is_currency_different, True)
        cons_chart.company_ids = False
        cons_chart._compute_is_currency_different()
        self.assertEqual(cons_chart.is_currency_different, False)

    def test_compute_group_ids_count(self):
        self.cons_chart._compute_group_ids_count()
        self.assertEqual(self.cons_chart.group_ids_count, len(self.cons_chart.group_ids))

    def test_compute_account_ids_count(self):
        self.cons_chart._compute_account_ids_count()
        self.assertEqual(self.cons_chart.account_ids_count, len(self.cons_chart.account_ids))

    def test_compute_period_ids_count(self):
        self.cons_chart._compute_period_ids_count()
        self.assertEqual(self.cons_chart.period_ids_count, len(self.cons_chart.period_ids))

    def test_action_open_groups(self):
        self.assertEqual(self.cons_chart.action_open_groups(), {
            'type': 'ir.actions.act_window',
            'name': 'Account Groups',
            'view_mode': 'tree,form',
            'res_model': 'consolidation.group',
            'target': 'current',
            'domain': [('chart_id', '=', self.cons_chart.id)],
            'context': {'default_chart_id': self.cons_chart.id},
        })

    def test_action_open_accounts(self):
        self.assertEqual(self.cons_chart.action_open_accounts(), {
            'type': 'ir.actions.act_window',
            'name': 'Consolidation Accounts',
            'view_mode': 'tree,form',
            'res_model': 'consolidation.account',
            'target': 'current',
            'domain': [('chart_id', '=', self.cons_chart.id)],
            'context': {'default_chart_id': self.cons_chart.id},
        })

    def test_action_open_period(self):
        self.assertEqual(self.cons_chart.action_open_period(), {
            'type': 'ir.actions.act_window',
            'name': 'Periods',
            'view_mode': 'tree,form',
            'res_model': 'consolidation.period',
            'target': 'current',
            'domain': [('chart_id', '=', self.cons_chart.id)],
            'context': {'default_chart_id': self.cons_chart.id},
        })
